


'''
Much thanks to staticfg, which served as a primer as I was puzzlling over this
'''

import libcst as cst
from autoplag import DirectedGraph, Chunk, isinstance_ControlFlow, isinstance_NonWhitespace
    
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

def build_cfg(ast_tree):
    cfg = DirectedGraph()    
    
    print('\nTree walk uwu')
    
    def first_line(node):
        try:
            return ast_tree.code_for_node(node).strip().split('\n')[0]
        except:
            return 'No code for type ' + type(node).__name__
    
    def treewalk(node, entry_chunk: Chunk):
        # iprint('treewalk', first_line(node))
        indent()
        
        ret_val = None
        
        # Basecase, boring statements
        if isinstance(node, cst.BaseSmallStatement):
            iprint('treewalk plain statement', first_line(node))
            entry_chunk.append(node)
            ret_val = entry_chunk
                                      
        # Container, needs to be iterated to get to SimpleStatementLine  
        elif isinstance(node, cst.IndentedBlock):
            iprint('treewalk indented block', type(node).__name__, first_line(node))
            for child in filter(isinstance_NonWhitespace, node.children):                                                        
                iprint('|__')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk)
                    
            ret_val = entry_chunk
        
        # Container, needs to be iterated to get to statements
        elif isinstance(node, cst.SimpleStatementLine):
            iprint('treewalk StatementLine', first_line(node))
            
            for child in filter(isinstance_NonWhitespace, node.children):                                                        
                iprint('|__')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk)
                    
            ret_val = entry_chunk
            # entry_chunk.body.append(node)
            # ret_val = entry_chunk
        
        elif isinstance_ControlFlow(node):
                        
            if isinstance(node, cst.For):
                iprint('treewalk For', first_line(node))
                
                # Make new blocks for each
                for_base = cfg.add_node(Chunk())
                for_base.append(node)
                cfg.add_edge(entry_chunk, for_base)
                
                loop_chunk_entry = cfg.add_node(Chunk())
                loop_chunk_exit = treewalk(node.body, loop_chunk_entry)
                
                cfg.add_edge(for_base, loop_chunk_entry)
                cfg.add_edge(loop_chunk_exit, for_base)
                
                for_gather = cfg.add_node(Chunk())
                cfg.add_edge(for_base, for_gather)
                
                ret_val = for_gather
            
            elif isinstance(node, cst.While):
                iprint('treewalk While', first_line(node))
                
                # Make new blocks for each
                while_base = cfg.add_node(Chunk())
                while_base.append(node)
                cfg.add_edge(entry_chunk, while_base)
                
                loop_chunk_entry = cfg.add_node(Chunk())
                loop_chunk_exit = treewalk(node.body, loop_chunk_entry)
                
                cfg.add_edge(while_base, loop_chunk_entry)
                cfg.add_edge(loop_chunk_exit, while_base)
                
                while_gather = cfg.add_node(Chunk())
                cfg.add_edge(while_base, while_gather)
                
                ret_val = while_gather
            
            elif isinstance(node, cst.If):
                iprint('treewalk If', first_line(node))
                
                # Make new blocks for each
                entry_chunk.append(node)
                
                if_gather = cfg.add_node(Chunk())
                cfg.add_edge(entry_chunk, if_gather)
                
                body_chunk_entry = cfg.add_node(Chunk())
                cfg.add_edge(entry_chunk, body_chunk_entry)
                
                body_chunk_exit = treewalk(node.body, body_chunk_entry)
                cfg.add_edge(body_chunk_exit, if_gather)
                
                if node.orelse:
                    bottom_chunk_entry = cfg.add_node(Chunk())
                    cfg.add_edge(entry_chunk, bottom_chunk_entry)
                    
                    bottom_chunk_exit = treewalk(node.orelse, bottom_chunk_entry)
                    
                    cfg.add_edge(bottom_chunk_exit, if_gather)
                
                ret_val = if_gather
                
            else:
                raise Exception()
            
        elif isinstance(node, cst.FunctionDef):
            iprint('treewalk FunctionDef:', first_line(node))
            
            ret_val = treewalk(node.body, entry_chunk)
        
        else:
            raise Exception(type(node).__name__ + ' must be a Function node or a node found within a function')
        
        undent()
        return ret_val
            
    assert(isinstance(ast_tree, cst.Module))
    for function in ast_tree.children:
        entry_chunk = cfg.add_node(Chunk())
        exit_chunk = treewalk(function, entry_chunk)
    
    return cfg