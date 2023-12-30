


'''
Much thanks to staticfg, which served as a primer as I was puzzlling over this
'''

from typing import List
import libcst as cst
from autoplag import DirectedGraph, Chunk, first_line, isinstance_ControlFlow, isinstance_NonWhitespace
    
indents = 0
def indent():
    global indents
    indents += 1
    
    if indents > 13:
        raise Exception()

def undent():
    global indents
    indents -= 1
    
def iprint(*kwargs):
    global indents
    indent_str = '    ' * indents
    print(indent_str, end='')
    print(*kwargs)

def build_cfgs(ast_tree):
    '''
    Builds CFGs, inserting nodes into a graph structure, where graph verticies are BBs (Chunks).
    Returns a list of CFGs, one per function. Each contains a .func member referencing the entry
    FunctionDef node
    
    Note: as python is pass-by-ref, nodes are simply references to the ones existing in the CST tree.
    We do not modify the CST nodes at all
     
    Control flow nodes are the last statement in a chunk. So the body of a control flow node is ref'd 
    twice, indirectly within the control flow node at the end of the Chunk and directly in the sucessor Chunks.
    '''
    
    
    print('\nTree walk uwu')
    
    def treewalk(node: cst.FunctionDef, entry_chunk: Chunk, cfg: DirectedGraph):        
        # Creates new chunk, adds to cfg, and sets order 
        def new_chunk():
            new_chunk = Chunk()
            new_chunk.order = len(cfg.objects)
            cfg.add_chunk(new_chunk)
            return new_chunk
        
        indent()
        
        ret_val = None
        
        # Basecase, boring statements
        if isinstance(node, cst.BaseSmallStatement):
            iprint('treewalk plain statement', first_line(node, ast_tree))
            entry_chunk.append(node)
            ret_val = entry_chunk
                                      
        # Container, needs to be iterated to get to SimpleStatementLine  
        elif isinstance(node, cst.IndentedBlock):
            iprint('treewalk indented block', first_line(node, ast_tree))
            for child in filter(isinstance_NonWhitespace, node.children):                                                        
                iprint('|__')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk, cfg)
                    
            ret_val = entry_chunk
        
        # Container, needs to be iterated to get to statements
        elif isinstance(node, cst.SimpleStatementLine):
            iprint('treewalk StatementLine', first_line(node, ast_tree))
            
            for child in filter(isinstance_NonWhitespace, node.children):                                                        
                iprint('|__')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk, cfg)
                    
            ret_val = entry_chunk
            # entry_chunk.body.append(node)
            # ret_val = entry_chunk
        
        elif isinstance_ControlFlow(node):
                        
            if isinstance(node, cst.For):
                iprint('treewalk For', first_line(node, ast_tree))
                
                # Make new blocks for each
                for_base = new_chunk()
                for_base.append(node)
                cfg.add_edge(entry_chunk, for_base)
                
                loop_chunk_entry = new_chunk()
                loop_chunk_exit = treewalk(node.body, loop_chunk_entry, cfg)
                
                cfg.add_edge(for_base, loop_chunk_entry)
                cfg.add_edge(loop_chunk_exit, for_base)
                
                # Do this first so the chunk order is before for_gather
                if node.orelse:
                    orelse_chunk_entry = new_chunk()
                    
                for_gather = new_chunk()
                
                if node.orelse:
                    cfg.add_edge(while_base, orelse_chunk_entry)
                    
                    orelse_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    
                    cfg.add_edge(orelse_chunk_exit, for_gather)
                
                cfg.add_edge(for_base, for_gather)
                
                ret_val = for_gather
            
            elif isinstance(node, cst.While):
                iprint('treewalk While', first_line(node, ast_tree))
                
                # Make new blocks for each
                while_base = new_chunk()
                while_base.append(node)
                cfg.add_edge(entry_chunk, while_base)
                
                loop_chunk_entry = new_chunk()
                loop_chunk_exit = treewalk(node.body, loop_chunk_entry, cfg)
                
                cfg.add_edge(while_base, loop_chunk_entry)
                cfg.add_edge(loop_chunk_exit, while_base)
                
                # Do this before while_gather so the chunk order is right
                if node.orelse:
                    orelse_chunk_entry = new_chunk()
                
                while_gather = new_chunk()
                cfg.add_edge(while_base, while_gather)
                
                if node.orelse:
                    cfg.add_edge(while_base, orelse_chunk_entry)
                    
                    orelse_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    
                    cfg.add_edge(orelse_chunk_exit, while_gather)
                    
                ret_val = while_gather
            
            elif isinstance(node, cst.If):
                iprint('treewalk If', first_line(node, ast_tree))
                
                # Make new blocks for each
                entry_chunk.append(node)
                
                body_chunk_entry = new_chunk()
                cfg.add_edge(entry_chunk, body_chunk_entry)
                
                body_chunk_exit = treewalk(node.body, body_chunk_entry)
                
                # Do this beofre if_gather so the chunk order is right
                if node.orelse:
                    orelse_chunk_entry = new_chunk()
                    
                if_gather = new_chunk()
                cfg.add_edge(body_chunk_exit, if_gather)
                
                if node.orelse:
                    cfg.add_edge(entry_chunk, orelse_chunk_entry)
                    
                    bottom_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    
                    cfg.add_edge(bottom_chunk_exit, if_gather)
                
                ret_val = if_gather
                
            else:
                raise Exception()
            
        elif isinstance(node, cst.FunctionDef):
            iprint('treewalk FunctionDef:', first_line(node, ast_tree))
            
            ret_val = treewalk(node.body, entry_chunk, cfg)
        
        else:
            raise Exception(type(node).__name__ + ' must be a Function node or a node found within a function')
        
        undent()
        return ret_val
            
    assert(isinstance(ast_tree, cst.Module))
    
    cfgs: List[DirectedGraph] = []
    
    for function in ast_tree.children:
        assert(isinstance(function, cst.FunctionDef))

        cfg = DirectedGraph()
        entry_chunk = Chunk()
        entry_chunk.order = len(cfg.objects)
        cfg.add_chunk(entry_chunk)
        
        exit_chunk = treewalk(function, entry_chunk, cfg)
        
        cfg.func = function
        
        cfgs.append(cfg)
    
    return cfgs