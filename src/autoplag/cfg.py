


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
        raise Exception('Indented more than a sane amount! (Is there a bug?)')

def undent():
    global indents
    indents -= 1
    
def iprint(*kwargs):
    to_print = ' '.join([str(k) for k in kwargs])
    
    global indents
    indent_str = '    ' * indents
    
    indented_lines = [indent_str + line for line in to_print.split('\n')]
    to_print = '\n'.join(indented_lines)

    print(to_print)

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
            # Note, the order of child nodes for control flow must stay consistent,
            # because later shuffle.py uses the order to reconstruct the ast
            # The DirectedGraph object will preserve edge order as insertion order
            
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
                
                body_chunk_exit = treewalk(node.body, body_chunk_entry, cfg)
                
                # Do this beofre if_gather so the chunk order is right
                if node.orelse:
                    orelse_chunk_entry = new_chunk()
                    
                if_gather = new_chunk()
                cfg.add_edge(body_chunk_exit, if_gather)
                
                if node.orelse:
                    cfg.add_edge(entry_chunk, orelse_chunk_entry)
                    
                    bottom_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    
                    cfg.add_edge(bottom_chunk_exit, if_gather)
                else:
                    cfg.add_edge(entry_chunk, if_gather)
                    
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
        cfg.entry = entry_chunk
        
        cfgs.append(cfg)
    
    return cfgs

def find_if_join_point():
    '''
    Cuz I'm not writing a dominiator algorithm
    We actually have enough info to get away with not using dominators for
    while and if
    '''

def add_cfg_to_ast(cfg: DirectedGraph, ast):    
    visited: set[Chunk] = set()
    
    def build_ast(curr_chunk: Chunk):
        indent()
        
        
        body = []
        
        while True:
            if curr_chunk in visited:
                break
            
            visited.add(curr_chunk)
            
            iprint('\nbuild ast for', ''.join([ast.code_for_node(nodelet).strip().split('\n')[0] for nodelet in curr_chunk]))
            
            children = cfg.children(curr_chunk)
            
            if len(children) == 0:
                break
            
            ends_in_ctrl = isinstance_ControlFlow(curr_chunk.stmts[-1].stmt)
            iprint('ends_in_ctrl', ends_in_ctrl)
            
            if ends_in_ctrl:
                for stmt in curr_chunk.stmts[:-1]:
                    body.append(cst.SimpleStatementLine(body=[stmt.stmt]))
   
                end_stmt = curr_chunk.stmts[-1].stmt
                
                assert len(children) >= 2
                
                if isinstance(end_stmt, cst.While):
                    iprint('(ast for while)')
                    
                    body_block = build_ast(children[0])
                    orelse_block = build_ast(children[1]) if len(children) == 2 else None
                    body.append(end_stmt.with_changes(body=body_block, orelse=orelse_block))
                    curr_chunk = children[-1]
                    
                elif isinstance(end_stmt, cst.For):
                    children = cfg.children(curr_chunk)
                    body_block = build_ast(children[0])
                    orelse_block = build_ast(children[1]) if len(children) == 2 else None
                    body.append(end_stmt.with_changes(body=body_block, orelse=orelse_block))
                    curr_chunk = children[-1]
                    
                elif isinstance(end_stmt, cst.If):
                    children = cfg.children(curr_chunk)
                    body_block = build_ast(children[0])
                    orelse_block = build_ast(children[1]) if len(children) == 2 else None
                    body.append(end_stmt.with_changes(body=body_block, orelse=orelse_block))
                    curr_chunk = children[-1]
                    
            else:
                # iprint('build ast for uncond jump sequence')
                
                # does not end in ctrl
                for stmt in curr_chunk.stmts:
                    body.append(cst.SimpleStatementLine(body=[stmt.stmt]))
   
                assert len(children) == 1
                
                if cfg.parents(children[0]) == curr_chunk:
                    curr_chunk = children[0]
                else:
                    # looks like we're coming into a merge point
              
        # end while True
                
        undent()
        
        iprint('Done building for this linear control path')  
                        
        block = cst.IndentedBlock(body=body)
        return block
        
    function: cst.FunctionDef = cfg.func
    entry_chunk = cfg.entry
    body_block = build_ast(entry_chunk)    
    function.with_changes(body=body_block)
    
    return function