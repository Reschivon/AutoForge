# AutoPlag

AutoPag is a tool that paraphrases code, rewriting it to _look_ different while keeping the same functionality. This does not do trivial changes like renaming variables, but rather semantic transformations on the AST itself. It should evade MOSS, cursory human checks, and all but the most sophisticated plagarism tools.

Limited to Python3 for this proof-of-concept.

This tool can very much be used for plagarism. That's the point -- I'm demonstating that MOSS is a rather poor defense and that plagarism is not only viable, but optimal in Computer Science. AutoPlag has been open sourced to inspire people to come up with better anticheat tools. 

Of course, by using this tool you are responsible for anything that happens to you. Cheat responsibly!

## Install
You need Python > 3.9, but the code you're feeding in can be any valid Python 3 code. You also need `libcst` installed, which is on `pypi`

For diagnostic fans, have `graphviz` installed

## Usage 

`python autoplag.py input-file.py`

## Transformations

Goal is to modify at least one line in every 3-line chunk to break MOSS fingerprinting. (The k-value is not exactly three lines but this is a good enough approximation for now)

1. Statement reordering. After building Def/Use chains (requiring CFG and RDA), we can generate predecessor/sucessor constraints for each statement and randomize the order under such constraints. Then we check if the 3-lines rule has been met for every line.

2. If the three line rule has not been met, then it's likely we have some tightly woven data dependencies, like
    ```
    b = a
    c = b
    d = c
    ``` 

    It's possible the expressions are trivial and without side effects like the above example, in which case, we'll do subexpression substitution. 

3. If expressions cannot be substituted (eg. it has side effects or longer than a hardcoded sus-threshold), then we'll break an expression into multiple temporaries. The only issue with this is producing plausible names for the temporaries beyond `temp1`, `temp2`, `temp3`

4. Comments and whitespace remain, which MOSS ignores, but by chance an eagle-eyed human can see that they were copied. This stage strips all comments and randomly changes single spaces to no-space and no-space to single space.

    ```
    x = y  may become  x=y
    ```

## AST Representation
In Python 3.10 (and now backported to 3.9) there is advanced native support for code-to-ast and ast-to-code conversion, which makes old tools like `astor` obsolete. By chance I also found a newer ~~ast~~ cst representation called PyCST, which is slightly better.

PyCST preseves whitespace and comments, allowing us to make a roundtrip from source to CST to source without losing any information. This way we can selectively mix n' match whitespace patterns to make it look human. Plus, PyCST has better documentation and API. 

