
import itertools
from typing import Dict, List, Set
import libcst as cst
from libcst.metadata import PositionProvider
from autoplag import DirectedGraph, AssignType, get_assignment_targets
        
def empty(l):
    return len(l) == 0

def first_line(node, ast):
    if isinstance(node, str):
        return node
    
    try:
        return ast.code_for_node(node).strip().split('\n')[0]
    except:
        return 'No code for type ' + type(node).__name__

def stringify(s, ast):
    return [first_line(ss, ast) for ss in s]

def rda(cfg: DirectedGraph, ast: cst.Module):    
    wrapper = cst.MetadataWrapper(ast)
    position = wrapper.resolve(PositionProvider)
    
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
            
    # print('all_defs', [name + ': ' + first_line(s, ast) for name, s in all_defs])
    
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
            
            # Do not put yourself in the kill set
            stmts_intersected.remove(stmt_data.stmt)
            stmt_data.kills.update(stmts_intersected)
            
    
    # Add dummy statements to empty chunks so the propagration works correctly
    for chunk in cfg.objects.values():
        if empty(chunk.stmts):
            chunk.append('Placeholder Statement')
            
    # Do IN/OUT
    j = 0
    while j < 10:
        j += 1
        changed = False
        for chunk in cfg.objects.values():
            chunk_size = len(chunk.stmts)
            for i in range(chunk_size): 
                # Get in set
                if i == 0:
                    sets_to_merge = list(c[-1].outs for c in cfg.parents(chunk))
                    
                    chunk[i].ins = set().union(*sets_to_merge)
                else:
                    chunk[i].ins = chunk[i - 1].outs
                                        
                # Gen and kill are disjoint, so no need to worry about order
                # Most RDA literature enforces this wierd precedence like OUT = GEN + (IN - KILL) 
                working_set = chunk[i].ins.copy()
                working_set.update(chunk.stmts[i].gens)
                working_set.difference_update(chunk.stmts[i].kills)
                
                # print('set compare', [id(s) for s in working_set], [id(s) for s in chunk[i].outs], working_set == chunk[i].outs)
                if working_set != chunk[i].outs: changed = True
                chunk[i].outs = working_set
                
        if not changed: break
            
    # Print gen/kill
    print()
    for chunk in cfg.objects.values():
        for stmt_data in chunk.stmts: 
            # if empty(stmt_data.gens): continue
            
            print(first_line(stmt_data.stmt, ast), ':', 
                # 'gens', [first_line(gen, ast) for gen in stmt_data.gens], \
                #   '\tkills', [first_line(s, ast) for s in stmt_data.kills], \
                  '\tins', [first_line(s, ast) for s in stmt_data.ins], \
                  '\n\t\touts', [first_line(s, ast) for s in stmt_data.outs] )
            
            print()
    