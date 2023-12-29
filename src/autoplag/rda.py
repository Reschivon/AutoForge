
import itertools
from typing import Dict, List
import libcst as cst
from autoplag import DirectedGraph, AssignType, get_assignment_targets
        
def empty(l):
    return len(l) == 0

def first_line(node, ast):
    try:
        return ast.code_for_node(node).strip().split('\n')[0]
    except:
        return 'No code for type ' + type(node).__name__
        
def rda(cfg: DirectedGraph, ast: cst.Module):    
    
    # Collect all definitions and build gen
    all_defs: List[str, AssignType] = []
    
    for chunk in cfg.objects.values():
        for stmt_data in chunk.stmts:
            
            gen_names = get_assignment_targets(stmt_data.stmt)
            if empty(gen_names): continue
            
            # Add this stmt to its gen set
            # Yes, it's kinda redundant to add a statment to its own gen set
            # This is just here to be symmetrical to the kill set -- which
            # also contains a List of AssignType to reference other parts of the code
            stmt_data.gens.add(stmt_data.stmt)
            
            # Add name -> stmt mapping to all_defs
            gen_pairs = zip(gen_names, [stmt_data.stmt] * len(gen_names))
            all_defs.extend(gen_pairs)
            
    print('all_defs', [name + ': ' + first_line(s, ast) for name, s in all_defs])
    
    # Find assignments and build kill         
    for chunk in cfg.objects.values():
        for stmt_data in chunk.stmts:
            # Get variable names of all gens
            gens = get_assignment_targets(stmt_data.stmt)
                        
            # Find all statements that generate a name that we kill here
            defs_intersected = list(filter(lambda deff: deff[0] in gens, all_defs))
            
            if empty(defs_intersected): continue
            
            names_intersected, stmts_intersected = zip(*defs_intersected)
            stmts_intersected = set(stmts_intersected)
            # Do not kill yourself
            stmts_intersected.remove(stmt_data.stmt)
            stmt_data.kills.update(stmts_intersected)
            
    # Print gen/kill
    for chunk in cfg.objects.values():
        for stmt_data in chunk.stmts: 
            if empty(stmt_data.gens): continue
            
            print('gens', [first_line(gen, ast) for gen in stmt_data.gens], \
                  '\tkills', [first_line(s, ast) for s in stmt_data.kills])
            
    # Do IN/OUT
            
            
            