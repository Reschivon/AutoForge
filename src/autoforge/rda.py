
import itertools
from typing import Collection, Dict, List, Set, Tuple
import libcst as cst
from libcst.metadata import PositionProvider
from autoforge import DirectedGraph, AssignType, first_line, \
    isinstance_AssignType, isinstance_ControlFlow, get_expression_ControlFlow
from autoforge.common_structures import Functional, first_col, isinstance_Definition, isinstance_Functional
        
def empty(l):
    '''
    Suprisingly useful
    '''
    return len(l) == 0

def stringify(s, ast):
    '''
    Calls first_line on a Collection of nodes
    '''
    return [first_line(ss, ast) for ss in s]

def gen_attr_name_nested(node):
    '''
    # So we may get nested assignntypes like x.y.z
    # In such a case we must generate a using name like 'x.y.z`
    # and not simply 'x.y' or 'z' or etc.
    '''
    if isinstance(node, cst.Name):
        # Base case
        return node.value
    elif isinstance(node, cst.Attribute):
        return gen_attr_name_nested(node.value) \
            + '.' \
            + gen_attr_name_nested(node.attr)
    
    else:
        raise Exception()
            
def get_usages(node: cst.CSTNode, cfgs=None):
    '''
    Return all used objects in a function. This handles regular statements,
    assignments (where the assign-target is ignored), function calls, etc. Skip control flow body
    
    Walk the tree, looking for used variables, and add such names to the uses list
        
    Why treewalk and not cst.Visitor? Because we do complex type checks like isinstance_AssignType
    Which is no supported by the visitor machinery
    '''
        
    uses: set[cst.Name] = set()
        
    if isinstance_Functional(node):
        found = False
        for func, cfg in cfgs:
            if func == node and hasattr(cfg, 'captures'):
                uses.update(cfg.captures)
                print('using', func.name.value, cfg.captures)
                found = True
                break
        if not found:
            raise Exception('RDA pass needed on', node.name.value)
    
    elif isinstance_Definition(node):
        pass
    
    elif isinstance(node, cst.Name):
        # Base case
        uses.add(node.value)
        
    elif isinstance(node, cst.Attribute):
                    
        uses.add(gen_attr_name_nested(node))
        
    elif isinstance(node, cst.CompFor):
        print(node)
        # For something like for a in b, a is NOT a use
        uses |= get_usages(node.iter, cfgs)
        if hasattr(node, 'inner_comp_for'): 
            uses |= get_usages(node.inner_comp_for)
        
    elif isinstance_AssignType(node):
        # Ignore the target part
        # Note CompFor is Assigntype but it's handled specially above
        uses |= get_usages(node.value, cfgs)
                    
    elif isinstance_ControlFlow(node):
        # For control flow, descend in to expression and body
        uses |= get_usages(get_expression_ControlFlow(node), cfgs)
        
        # uses |= get_usages(node.body)
        # if node.orelse: uses |= get_usages(node.orelse)
        
    elif isinstance(node, cst.Call):
        # For calls, it uses the calle state and arguments, so they are
        # counted as USEs. Additionally, the function itself is counted too
        
        if isinstance(node.func, cst.Attribute):
            # Caller name
            uses.add(gen_attr_name_nested(node.func.value))
            # function name
            uses.add(node.func.attr.value)
            
            for a in node.args:
                uses |= get_usages(a, cfgs)
            
        elif isinstance(node.func, cst.Name):
            # function name
            uses.add(gen_attr_name_nested(node.func))
            for a in node.args:
                uses |= get_usages(a, cfgs)
        else:
            raise Exception()
                    
    else:
        assert isinstance(node, cst.CSTNode)
        # Recurse all children, no special treatment
        for child in node.children:
            uses |= get_usages(child, cfgs)
                
    return uses

# TODO: list of functions that do not modify, ie. range
# Use lib to resolve args
def get_assignments(node: AssignType) -> Set[str]:
    '''
    Given a cst.CSTNode, if it is any assignment type like `a = b` or `a = b = c` it will return
    all the assigned-to variables as str. Skip control flow body
    
    Potential modifications count too
    
    so self.xxx() modifies self, and function args modify function args
    
    If there are no assigned-to variables or the node is not an assigment type, then you'll get 
    empty list
    '''
    targets: Set[str] = set()
              
    if isinstance_Functional(node):
        targets.add(node.name.value)
           
    elif isinstance_Definition(node):
        pass
    
    elif isinstance(node, cst.CompFor):
        targets |= get_assignments(node.target)
    
    elif isinstance_ControlFlow(node):
        # For control flow, count the expression, skip body
        
        if isinstance(node, cst.For):
            targets |= get_assignments(node.target)
            
        # TODO; let's just assume the expression of control flow NEVER
        # mutates.
        # targets |= get_assignments(get_expression_ControlFlow(node))
        
        # targets |= get_assignments(node.body)
        # if node.orelse: targets |= get_assignments(node.orelse)
            
    elif isinstance(node, cst.Name):
        # Base case
        targets.add(node.value)
     
    elif isinstance(node, cst.Assign):
        for target in node.targets:
            targets |= get_assignments(target.target)
                   
    elif isinstance(node, cst.AugAssign):
        targets |= get_assignments(node.target)
        
    elif isinstance(node, cst.AnnAssign) and node.value: # Not always has value, which defeats purpose of assign
        targets |= get_assignments(node.target)
        
    elif isinstance(node, cst.Attribute):    
        targets.add(gen_attr_name_nested(node))
        
    elif isinstance(node, cst.Call):
        # For calls, it may mutate the calle and arguments, so they are
        # counted as assignments.
        
        # TODO assume args aren't mutated
                
        if isinstance(node.func, cst.Attribute):
            # Caller name
            targets.add(gen_attr_name_nested(node.func.value))
           
            # for a in node.args:
            #     targets |= get_assignments(a)
            
        elif isinstance(node.func, cst.Name):
            # for a in node.args:
            #     targets |= get_assignments(a)
            pass
        else:
            raise Exception()
    else:
        assert isinstance(node, cst.CSTNode)
        # Recurse all children, no special treatment
        for child in node.children:
            targets |= get_assignments(child)
    
    return targets

def get_params(node: Functional):
    ppp = []
    for p in node.params:
        ppp.append(p.name.value)
    return ppp

def names_interfere(a, b):
    '''
    Given dot separated variables names, like 
    self.x.y or self, or x, or a.x
    
    Determine if one name is the parent object of another. The purpose is to
    deduce if modifying one variable could potentially invaldate the other.
    
    For example, modifiying 'self' could potentially redefine 'self.x',
    (or vice versa!) so the function returns True. However, changing self.y
    does not influence self.x.
    
    We assume no aliasing, so even if stuff intereferes like root.next.next.prev
    and root.next, this will not identify it.
    
    Is a symmetric function
    '''
    # Easy case, same name
    if a == b: return True
    
    asplit = a.split('.')
    bsplit = b.split('.')
    
    # Same length but not the same? (ie. x.y.z1 vs x.y.z2)
    # One could not possibly be the parent object of the other
    if len(asplit) == len(bsplit): return False
    
    # See if they share a root
    for apart, bpart in zip(a.split('.'), b.split('.')):
        if apart == bpart:
            return True
    
    # Different lengths, shares no root (a.b.c vs x.y.z)
    return False
    
def any_name_interferes(a: Collection, b: str):
    '''
    If any element of a satisfies name_contains for b 
    '''
    for apart in a:
        if names_interfere(apart, b):
            return True
    return False

def intersects(a: Collection, b: Collection) -> bool:
    return len(set(a).intersection(set(b))) > 0
    
def run_rda(cfg: DirectedGraph, ast: cst.Module, cfgs):  
    '''
    Given a CFG (generated by cfg.py) and the original cst, this will compute IN/OUT sets per instruction
    
    https://en.wikipedia.org/wiki/Reaching_definition
    
    Note that nothing is returned, rather, the IN/OUT sets are added to the cfg. You can access by iterating 
    over each statement in each basicblock of the cfg. Within each statement are the .ins and .out members
    
    for chunk in cfg:
        for stmt_data in chunk.stmts:
            print(stmt_data.ins, stmt_data.outs)
    '''  
    
    print('\n\n====== RDA results for', first_line(cfg.func, ast))

    
    all_defs: Set[Tuple[str, AssignType]] = set()
    
    # Collect all definitions and build gen set
    for chunk in cfg:
        for stmt_data in chunk.stmts:
            
            gen_names = get_assignments(stmt_data.node)
            gens = set(zip(gen_names, [stmt_data.node] * len(gen_names)))
            
            if empty(gens): continue
            
            # Add this stmt to its gen set
            stmt_data.gens.update(gens)
            
            # Add to all_defs
            all_defs.update(gens)
                        
    # Add function arguments to all_defs
    # Note the statement reference will just be the FunctionDef itself
    arg_gen_names = get_params(cfg.func.params)
    arg_gen_pairs = set(zip(arg_gen_names, [cfg.func] * len(arg_gen_names)))
    all_defs.update(arg_gen_pairs)
    
    print('all defs', [name + ': ' + first_line(s, ast) for name, s in all_defs])

    # Find assignments and build kill         
    for chunk in cfg:
        for stmt_data in chunk.stmts:
            # Get variable names of all gens
            gens = get_assignments(stmt_data.node)
                        
            # Get all statements whose generated name gets killed here
            defs_intersected: Set[Tuple[str, AssignType]] = set()
            for gen_name in gens:
                for def_name, def_stmt in all_defs:
                    if names_interfere(gen_name, def_name):
                        defs_intersected.add((gen_name, def_stmt))
                        
            if empty(defs_intersected): continue
            
            # Do not put yourself in the kill set
            defs_intersected = [deff for deff in defs_intersected if deff[1] != stmt_data.node]
            stmt_data.kills.update(defs_intersected)
            
    
    # Add dummy statements to empty chunks so the propagration works correctly
    for chunk in cfg:
        if empty(chunk.stmts):
            chunk.append(cst.Comment('# Empty BB')) 
            
    # Do IN/OUT
    while True:
        # If any OUT set is updated, this is set to True
        changed = False
        
        for chunk in cfg:
            chunk_size = len(chunk.stmts)
            for i in range(chunk_size): 
                # Get the UNION of predecessors. Note predecessors are _statements_ and not BBs as some other
                # implementations do
                if i == 0:
                    # Since we can't access statements directly, we'll actually get the predecessor _chunks_
                    # and then extract the last statement from each
                    sets_to_merge = [c[-1].outs for c in cfg.parents(chunk)]
                    
                    # If first one, then add params
                    if chunk.order == 0 and i == 0:
                        sets_to_merge.append(arg_gen_pairs)
                    
                    # If this is the first block, then ins include the arguments
                    chunk[i].ins = set().union(*sets_to_merge)
                else:
                    chunk[i].ins = chunk[i - 1].outs
                                        
                # OUT = GEN + (IN - KILL) 
                working_set = chunk[i].ins.copy()
                working_set.update(chunk.stmts[i].gens)
                working_set.difference_update(chunk.stmts[i].kills)
                
                if working_set != chunk[i].outs: changed = True
                
                chunk[i].outs = working_set
            
        # The only way to end the loop is here    
        if not changed: break
    
    # Set deps
    
    # store captures for later
    cfg.captures = set()
        
    # TODO handle nasty edge cases better
    for chunk in cfg:
        for stmt_data in chunk.stmts:
            # Figure out uses
            stmt_data.uses = get_usages(stmt_data.node, cfgs)
                
            # Map each USE set item (a simple string) to its corresponding statement
            # Is done by intersecting IN set with our use set
            for used_name in stmt_data.uses:
                success = False
                for in_name, in_stmt in stmt_data.ins:
                    if names_interfere(used_name, in_name)  :              
                        stmt_data.deps.add((used_name, in_stmt))
                        success = True
                if not success:
                    # Uses a definition that's not defined in the function, capture
                    cfg.captures.add(used_name)
                
            # Find all members of IN set that intersect our kill set
            stmt_data.deps.update(stmt_data.kills.intersection(stmt_data.ins))
                    
            # Make deps satemtns-only
            stmt_data.deps = set(map(lambda t:t[1], stmt_data.deps))
                    
            # Remove all deps that refer to function args (Just for TODO)
            if cfg.func in stmt_data.deps: stmt_data.deps.remove(cfg.func)
                        
    # Print gen/kill
    print()
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            
            print(first_line(stmt_data.node, ast), 
                    # 'gens', [first_line(gen, ast) for gen in stmt_data.gens], \
                    #   '\tkills', [first_line(s, ast) for s in stmt_data.kills], \
                  '\n\tuses', stringify(stmt_data.uses, ast), \
                  '\n\tkills', stringify(stmt_data.kills, ast), \
                  '\n\tgens', stringify(first_col(stmt_data.gens), ast), \
                  '\n\tins', stringify(stmt_data.ins, ast), \
                  '\n\touts', stringify(stmt_data.outs, ast))
                  
            
            print()
        
    # Print deps
    print()
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            
            print(first_line(stmt_data.node, ast), \
                  '\n\tDEPS:', 
                # 'gens', [first_line(gen, ast) for gen in stmt_data.gens], \
                #   '\tkills', [first_line(s, ast) for s in stmt_data.kills], \
                  ' ', [first_line(s, ast) for s in stmt_data.deps] )
            
            print()
    