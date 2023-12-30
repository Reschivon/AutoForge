# AutoPlag

AutoPag is a tool that paraphrases code, rewriting it to _look_ different while keeping the same functionality. This does not do trivial changes like renaming variables, but rather semantic transformations on the AST itself. It should evade MOSS, cursory human checks, and all but the most sophisticated plagarism tools.

Limited to Python3 for this proof-of-concept.

> Ethics note: this tool can definitely be used for plagarism. That's the point -- I'm demonstating that MOSS is a rather poor defense and that plagarism is not only viable, but optimal in Computer Science. AutoPlag has been open sourced to inspire people to come up with better anticheat tools. 

Of course, by using this tool you are responsible for anything that happens to you. Cheat responsibly!


## Todo
- parse classes correctly, and nested functions
- function calle object is a dependency
- function calls should assumed to modify the arguments and calle (if applicalbe)
- in for loop comprehensions, the iteration variable is not USE
- function call name is not a USE
- function parameters should be added to first IN

## Install
You need Python > 3.9, but the code you're feeding in can be any valid Python 3 code. You also need `libcst` installed, which is on `pypi`

For diagnostic fans, have `graphviz` installed

## Usage 

`python autoplag.py input-file.py`

## Transformations

Goal is to modify at least one line in every 3-line chunk to break MOSS fingerprinting. (The k-value is not exactly three lines but this is a good enough approximation for now)

1. Statement reordering. After building Use-Def chains (requiring CFG and RDA), we can generate a set of predecessor constraints for each statement that will define what reorderings preserve semantics. For example, for a statement x, USE-DEF(x) U [KILL(x) ∩ IN(x)] are the set of instructions that must come before x. (Where USE-DEF(x) is the set of dominating definitions corresponding to our USE set) (We have to union the KILL set with IN set to only get valid dominating definitions at the statement)

    As a rule of thumb, x should not move outside its scope. It can if it does not clash with with other definitions of x at the control merge/split point, but generally checking this is rather tedious and such opportunities are rare in practice.
    
    There are cases where we can move x to the scope preheader, if it has no dependencies on anything within the scope. (Note: for this, check dependencies before and after)
    
    If x is dependent on a definition after it (such as for a loop) then x must stay in scope and come before the definition.

    Then we check if the 3-line rule has been met for every line.

2. If the three line rule has not been met, then it's likely we have some tightly woven data dependencies, like
    ```
    b = a
    c = b + x + y + z + zz + zzz
    d = c
    ``` 

    It's possible the expressions are trivial like line 1 and 3, allowing us to do subexpression elimination to saisfy the 3-line rule, but such cases are rare because it looks awkward to the programmer. However, we can do the opposite by breaking line 2 (long fellow) into subexpressions. We'll split the subexpression tree into 2 (or more) parts, assigning it to a plausible temporary.
    
     ```
    b = a
    tempc = b + x + y
    temppc = z + zz + zzz
    c = tempc + temppc
    d = c
    ``` 

    The only issue with this is producing plausible names for the temporaries beyond `temp1`, `temp2`, `temp3`

4. Comments and whitespace remain, which MOSS ignores, but by chance an eagle-eyed human can see that they were copied. This stage strips all comments and randomly changes single spaces to no-space and no-space to single space.

    ```
    x = y  may become  x=y
    ```

## AST Representation
In Python 3.10 (and now backported to 3.9) there is advanced native support for code-to-ast and ast-to-code conversion, which makes old tools like `astor` obsolete. I also found a newer ~~ast~~ cst representation called libCST, which is slightly better.

PyCST preseves whitespace and comments, allowing us to make a roundtrip from source to CST to source without losing any information. This way we can selectively mix n' match whitespace patterns to make it look human. Plus, libCST has better documentation and API. 

There's also RedBaron but it hasn't been maintained for a while.

