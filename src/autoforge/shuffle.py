
import random
from typing import Dict, List, Tuple
import libcst as cst
from autoforge import DirectedGraph, StmtData, Chunk
from autoforge.printlib import indent, print, stringify, undent


def random_index(list: List, prefer_not=None):
    if prefer_not is None:
        return random.randint(0, len(list) - 1)
    
    if list == [prefer_not]:
        return 0
    else:
        ii = list.index(prefer_not)
        index = random.randint(0, len(list) - 2)
        if index >= ii: index += 1
        
        return index

def shuffle(cfg: DirectedGraph, ast: cst.Module):
    
    # Build a map from stmts to their Chunk
    stmt_order: Dict[cst.CSTNode, StmtData] = {}
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            assert isinstance(stmt_data.node, cst.CSTNode)
            stmt_order[stmt_data.node] = stmt_data
            
            
    # Before we do the inversion below, we have to compute scope limits
    # Everything stays in its original scope during mixing    
    # There are ways to move them but it's complicated to compute, and the prerequisites
    # make such moves unnlikely
    
            
    # If given two statements (x, y) such that x has a dep on y and y executes after x,
    # then invert the dependency so that y has a dep on x
    # This way all deps are guranteed to come before, which is neccessary as we rebuild the ast
    # in forward order
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            # invert deps
            for dep_stmt in stmt_data.deps.copy(): # Iter on copy because we modify the original 
                # Since dep_stmt is a CSTNode and not a StmtData, we need to 
                # extract its order using the `stmt_order` map
                assert isinstance(dep_stmt, cst.CSTNode)
                if stmt_data.order < stmt_order[dep_stmt].order:
                    # Invert the dep, so dep_stmt has it
                    stmt_order[dep_stmt].deps.add(stmt_data.node)
                    # Remove the dep from the original stmt
                    stmt_data.deps.remove(dep_stmt)
                    
                    
    # Print deps
    # print('Mixer inverted deps')
    # for chunk in cfg:
    #     for stmt_data in chunk.stmts: 
            
    #         print(first_line(stmt_data.node, ast), '\tDEPS:', 
    #             # 'gens', [first_line(gen, ast) for gen in stmt_data.gens], \
    #             #   '\tkills', [first_line(s, ast) for s in stmt_data.kills], \
    #               ' ', [first_line(s, ast) for s in stmt_data.deps] )
            
    #         print()
            
    # Build ordered list of Chunks from cfg
    chunks = list(cfg.objects.values())
    chunks.sort(key=lambda chunk: chunk.order)
    
    # Shuffle
    print('\n\n====== Shuffling', cfg.func)
    
    # chunk.stmts -> insertable -> new_stmts
    for chunk in chunks:
        print('\nIn chunk', chunk.order)
        
        indent()
        
        # If last is control flow, then do not move it, add it back at the end
        last = None
        if chunk.end_in_control_flow():
            last = chunk.stmts[-1]
            del chunk.stmts[-1]
        
        new_stmts: List[Chunk] = []
        
        insertable: List[cst.CSTNode] = list()
        
        def insert_stmts_with_no_deps():
            for stmt in chunk.stmts.copy():
                if len(stmt.deps) == 0:
                    insertable.append(stmt)
                    chunk.stmts.remove(stmt)
                    
        # No-deps statements are always insertable
        print('\tinitial stmts', chunk.stmts)
        print('\tinitial deps', [stmt.deps for stmt in chunk.stmts])
        insert_stmts_with_no_deps()
        
        while len(insertable) > 0:            
            # Insert random allowable
            print('\tinsert choices', insertable)
            
            # i_to_remove = random_index(insertable, prefer_not=insertable[-1])
            i_to_remove = random_index(insertable)
            new_stmts.append(insertable[i_to_remove])
            del insertable[i_to_remove]
            
            print('inserted', new_stmts[-1])
            
            # Recompute deps (for all chunks after)
            for recmp_chunk in chunks:
                if recmp_chunk.order < chunk.order: continue
                
                for stmt in recmp_chunk.stmts:
                    # Remove dependency if it was just inserted
                    if new_stmts[-1].node in stmt.deps:
                        stmt.deps.remove(new_stmts[-1].node)
            
            # Recompute insertable
            insert_stmts_with_no_deps()
            print()

        assert len(chunk.stmts) == 0, 'remaning stmts: ' + str(stringify(chunk.stmts))
        
        # Add back control flow, if applicable
        if last is not None:
            new_stmts.append(last)
            
            # Recompute deps (for all chunks after)
            # TODO do not repeat this chunk
            for recmp_chunk in chunks:
                if recmp_chunk.order < chunk.order: continue
                
                for stmt in recmp_chunk.stmts:
                    # Remove dependency if it was just inserted
                    if new_stmts[-1].node in stmt.deps:
                        stmt.deps.remove(new_stmts[-1].node)
            
        # Swap chunk stmts with new stmts
        chunk.stmts = new_stmts
        
        undent()
        
    
    # print('Regenerated:', ast_tree.code, sep='\n')
    