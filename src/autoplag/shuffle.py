
import random
from typing import Dict, List, Tuple
import libcst as cst
from autoplag import DirectedGraph, StmtData, first_line
from autoplag import Chunk
from autoplag.rda import stringify

def shuffle(cfg: DirectedGraph, ast: cst.Module):
    
    # Build a map from stmts to their Chunk
    stmt_order: Dict[cst.CSTNode, StmtData] = {}
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            stmt_order[stmt_data.stmt] = stmt_data
            
            
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
                if stmt_data.order < stmt_order[dep_stmt].order:
                    # Invert the dep, so dep_stmt has it
                    stmt_order[dep_stmt].deps.add(stmt_data.stmt)
                    # Remove the dep from the original stmt
                    stmt_data.deps.remove(dep_stmt)
                    
                    
    # Print deps
    print('Mixer inverted deps')
    for chunk in cfg:
        for stmt_data in chunk.stmts: 
            
            print(first_line(stmt_data.stmt, ast), '\tDEPS:', 
                # 'gens', [first_line(gen, ast) for gen in stmt_data.gens], \
                #   '\tkills', [first_line(s, ast) for s in stmt_data.kills], \
                  ' ', [first_line(s, ast) for s in stmt_data.deps] )
            
            print()
            
    # Build ordered list of Chunks from cfg
    chunks = list(cfg.objects.values())
    chunks.sort(key=lambda chunk: chunk.order)
    
    # Shuffle
    print('Shuffling', first_line(cfg.func, ast))
    
    # chunk.stmts -> insertable -> new_stmts
    for chunk in chunks:
        print('\nIn chunk', chunk.order)
        
        new_stmts: List[Chunk] = []
        
        insertable: List[cst.CSTNode] = list()
        
        def insert_stmts_with_no_deps():
            for stmt in chunk.stmts.copy():
                if len(stmt.deps) == 0:
                    insertable.append(stmt)
                    chunk.stmts.remove(stmt)
                    
        # No-deps statements are always insertable
        print('initial stmts', stringify(chunk.stmts, ast))
        print('initial deps', [stringify(stmt.deps, ast) for stmt in chunk.stmts])
        insert_stmts_with_no_deps()
        
        while len(insertable) > 0:            
            # Insert random allowable
            i_to_remove = random.randint(0, len(insertable) - 1)
            new_stmts.append(insertable[i_to_remove])
            del insertable[i_to_remove]
            
            print('\tinsert choices', stringify(insertable, ast))
            print('inserted', first_line(new_stmts[-1], ast))
            
            # Recompute deps (for all chunks after)
            for recmp_chunk in chunks:
                if recmp_chunk.order < chunk.order: continue
                
                for stmt in recmp_chunk.stmts:
                    # Remove dependency if it was just inserted
                    if new_stmts[-1].stmt in stmt.deps:
                        stmt.deps.remove(new_stmts[-1].stmt)
            
            # Recompute insertable
            insert_stmts_with_no_deps()
            print()

        assert len(chunk.stmts) == 0, 'remaning stmts: ' + str(stringify(chunk.stmts, ast))
        
        # Swap chunk stmts with new stmts
        chunk.stmts = new_stmts
        
    
    # print('Regenerated:', ast_tree.code, sep='\n')
    