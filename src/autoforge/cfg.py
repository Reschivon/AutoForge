


'''
Much thanks to staticfg, which served as a primer as I was puzzlling over this
'''

from typing import Dict, List, Tuple
import libcst as cst
from autoforge import DirectedGraph, Chunk, isinstance_ControlFlow, isinstance_Whitespace
from autoforge.common_structures import Functional, isinstance_Definition, isinstance_Functional
from autoforge.printlib import indent, undent, print

def build_cfgs(ast_tree):
    '''
    Returns a list of tuples (Functional, CFG), one per function. Creates a graph structure, where verticies are 
    BBs (Chunks). Each CFG contains a .func member referencing the corresponding function node,
    and a .entry member for first Chunk
    
    Note: This returns a list in nesting order, such that nested functions ALWAYS come before
    their parents. This is because, when we replace functions with their nested counterparts later,
    we need to swap functions in nesting order (smallest to largest) or else overwrite the small ones. 
        
    Note: as python is pass-by-ref, nodes are simply references to the ones existing in the CST tree.
    We do not modify the CST nodes at all
     
    Control flow nodes are the last statement in a chunk. So the body of a control flow node is ref'd 
    twice, indirectly within the control flow node at the end of the Chunk and directly in the sucessor Chunks.
    '''
    
    assert(isinstance(ast_tree, cst.Module))
    cfgs: List[Tuple[Functional, DirectedGraph]] = []
        
    print('\nTree walk uwu')
    
    def treewalk(node: cst.CSTNode, entry_chunk: Chunk, cfg: DirectedGraph):  
        '''
        When called on a Module or ClassDef: returns nothing, adds child functionDefs to cfg list
        When called on a FunctionDef: returns nothing, adds the CFG for the function to cfg list, and any child functions
        When called on structure within a function: converts the structure to cfg subgraph, adds to cfg object, returns new active chunk
        '''      
        # Creates new chunk, adds to cfg, and sets order 
        def new_chunk():
            new_chunk = Chunk()
            new_chunk.order = len(cfg.objects)
            cfg.add_chunk(new_chunk)
            return new_chunk
        
        indent()
        
        ret_val = None
        
        # Basecase, boring statements
        if isinstance(node, cst.Module) or isinstance(node, cst.ClassDef) or entry_chunk is None:
            print('treewalk', type(node).__name__, ':', node)
            
            # Recurse into children, searching for FunctionDefs
            for child in node.children:
                print('└──')
                treewalk(child, entry_chunk, cfg)
                
        elif isinstance(node, cst.BaseSmallStatement) or isinstance(node, cst.With): # TODo deal with With properly
            print('treewalk plain statement', node)
            entry_chunk.append(node)
            ret_val = entry_chunk
            
        elif isinstance_Whitespace(node):
            # Ignore
            print('treewalk whitespace (ignored)', node)
            ret_val = entry_chunk
    
        # Container, needs to be iterated to get to SimpleStatementLine  
        elif isinstance(node, cst.IndentedBlock):
            print('treewalk indented block', node)
            # for child in filter(isinstance_NonWhitespace, node.children):                                                        
            for child in node.children:                                                        
                print('└──')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk, cfg)
                    
            ret_val = entry_chunk
        
        # Container, needs to be iterated to get to statements
        elif isinstance(node, cst.SimpleStatementLine):
            print('treewalk StatementLine', node)
            
            # for child in filter(isinstance_NonWhitespace, node.children):                                                        
            for child in node.children:   
                print('└──')
                
                # Reassign entry_chunk continuously
                entry_chunk = treewalk(child, entry_chunk, cfg)
                    
            ret_val = entry_chunk
            # entry_chunk.body.append(node)
            # ret_val = entry_chunk
        
        elif isinstance_ControlFlow(node):
            # Note, the order of child nodes for control flow must stay consistent,
            # because later shuffle.py uses the order to reconstruct the ast
            # The DirectedGraph object will preserve edge order as insertion order
            
            # Also, the `orelse` clauses in For and While connect back to the base
            # chunk to ease the process of converting back to ast
            if isinstance(node, cst.For):
                print('treewalk For', node)
                
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
                    cfg.add_edge(for_base, orelse_chunk_entry)
                    
                    orelse_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    cfg.add_edge(orelse_chunk_exit, for_base)
                    
                for_gather = new_chunk()                    
                
                cfg.add_edge(for_base, for_gather)
                
                ret_val = for_gather
            
            elif isinstance(node, cst.While):
                print('treewalk While', node)
                
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
                    cfg.add_edge(while_base, orelse_chunk_entry)
                    
                    orelse_chunk_exit = treewalk(node.orelse.body, orelse_chunk_entry, cfg)
                    cfg.add_edge(orelse_chunk_exit, while_base)
                
                while_gather = new_chunk()
                cfg.add_edge(while_base, while_gather)                    
                    
                ret_val = while_gather
            
            elif isinstance(node, cst.If):
                print('treewalk If', node)
                
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
            
        elif isinstance_Functional(node):
            print('treewalk FunctionDef:', node)
            
            # Prepare new cfg for this function
            func_cfg = DirectedGraph()
            func_entry_chunk = Chunk()
            func_entry_chunk.order = 0
            func_cfg.add_chunk(func_entry_chunk)
            
            # Treewalk, append function contents to cfg
            exit_chunk = treewalk(node.body, func_entry_chunk, func_cfg)
            
            func_cfg.func = node
            func_cfg.entry = func_entry_chunk
            
            cfgs.append((node, func_cfg))
        
            # Returns parent chunk
            entry_chunk.append(node)
            ret_val = entry_chunk
        
        else:
            raise Exception(type(node).__name__ + ' not handled in treewalk, probably bug')
        
        undent()
        return ret_val
    
    # Prepare root default cfg that holds everything
    func_cfg = DirectedGraph()
    func_entry_chunk = Chunk()
    func_entry_chunk.order = 0
    func_cfg.add_chunk(func_entry_chunk)
    
    # Treewalk, append function contents to cfg
    exit_chunk = treewalk(ast_tree, func_entry_chunk, func_cfg)
    
    func_cfg.func = ast_tree
    func_cfg.entry = func_entry_chunk
    
    cfgs.append((ast_tree, func_cfg))
    
    # treewalk(ast_tree, None, None)
            
    return cfgs

def find_if_join_point(ordered_chunks: List[Chunk], cfg: DirectedGraph, start_chunk: Chunk):
    '''
    Cuz I'm not writing a DF algorithm
    We actually have enough info to get away with not needing dominators for
    While and For. However, for `If` we do need the dominance frontier
    '''
    
    seen: set[Chunk] = set()
    seen.add(start_chunk)
    start_chunk.nesting = 0
    
    i = start_chunk.order
    while True:
        i += 1
        curr_chunk = ordered_chunks[i]
        assert not hasattr(curr_chunk, 'nesting')
        parents = cfg.parents(curr_chunk)
        
        # Compute nesting
        if len(parents) == 2 \
            and parents[0].order < curr_chunk.order \
            and parents[1].order < curr_chunk.order:
            # Join point, either between THEN and ELSE branches,
            # or between THEN and IF header
            # This triggers also on While/For heads, with one parent being the body and one being the predecessor:
            # we don't want this to happen and thus also check if the parent orders are both less
            # print('Merger', parents[0].order, parents[1].order)
            # print('      ', parents[0].nesting, parents[1].nesting)
            if parents[0].nesting == parents[1].nesting:
                curr_chunk.nesting = parents[0].nesting - 1
                # print(curr_chunk.nesting)
            else:
                curr_chunk.nesting = min(parents[0].nesting, parents[1].nesting)
                # print(curr_chunk.nesting)
        elif len(parents) == 1:
            curr_chunk.nesting = parents[0].nesting + 1
        else:
            # While/For head
            assert len(parents) == 2
            curr_chunk.nesting = parents[0].nesting if hasattr(parents[0], 'nesting') else parents[1].nesting
            
        if curr_chunk.nesting == 0: 
            # print('join point of', start_chunk.order, 'is', curr_chunk.order)
            
            # Return from the function and clean the attributes we made
            for i in range(start_chunk.order, i + 1): 
                delattr(ordered_chunks[i], 'nesting')
            return curr_chunk

def cfg_to_ast(cfg: DirectedGraph, ast, remove_comments=True):  
    
    print('\nBuild AST for', cfg.func)
    
    # Build ordered chunks
    ordered_chunks: List[Chunk] = [None] * len(cfg.objects) 
    for chunk in cfg:
        ordered_chunks[chunk.order] = chunk
    for chunk in ordered_chunks:
        assert chunk is not None
      
    visited: set[Chunk] = set()
    
    def build_ast(curr_chunk: Chunk):
        indent()
         
        body = []
        
        while True:
            if curr_chunk in visited:
                break
            
            visited.add(curr_chunk)
            
            print('==> Build AST for chunk #', curr_chunk.order) 
            # print('\n'.join([ast.code_for_node(nodelet).strip().split('\n')[0] for nodelet in curr_chunk]),)
            
            children = cfg.children(curr_chunk)
            
            ends_in_ctrl = curr_chunk.end_in_control_flow()
            
            if ends_in_ctrl:
                normal_stmt_end = len(curr_chunk.stmts) - 1
            else:
                normal_stmt_end = len(curr_chunk.stmts)
                
            for stmt in curr_chunk.stmts[:normal_stmt_end]:
                if remove_comments \
                    and isinstance(stmt.node, cst.Expr) \
                    and isinstance(stmt.node.value, (cst.Comment, cst.SimpleString)): 
                    continue
                
                elif isinstance(stmt.node, cst.Comment):
                    continue
                
                elif isinstance_Definition(stmt.node):
                    # Do not wrap Definitions in a SimpleStatementLine
                    body.append(stmt.node)
                elif isinstance(stmt.node, cst.With): # TODO properly handle with
                    # Do not wrap With in a SimpleStatementLine
                    body.append(stmt.node)
                else:
                    # Wrap these non-defs in in SimpleStatementLine
                    body.append(cst.SimpleStatementLine(body=[stmt.node]))
            
            if len(children) == 0: 
                assert not ends_in_ctrl
                break
            
            if ends_in_ctrl:
                end_stmt = curr_chunk.stmts[-1].node
                
                assert len(children) >= 2
                
                if isinstance(end_stmt, cst.While):
                    print('(ast for while)')
                    
                    end_stmt = end_stmt.with_changes(body=build_ast(children[0]))
                    if len(children) == 3: end_stmt = end_stmt.with_changes(orelse=cst.Else(build_ast(children[1])))
                    body.append(end_stmt)
                    curr_chunk = children[-1]
                    
                elif isinstance(end_stmt, cst.For):
                    children = cfg.children(curr_chunk)
                    end_stmt = end_stmt.with_changes(body=build_ast(children[0]))
                    if len(children) == 3: end_stmt = end_stmt.with_changes(orelse=cst.Else(build_ast(children[1])))
                    body.append(end_stmt)
                    curr_chunk = children[-1]
                    
                elif isinstance(end_stmt, cst.If):
                    children = cfg.children(curr_chunk)
                    
                    join_chunk = find_if_join_point(ordered_chunks, cfg, curr_chunk)
                    visited.add(join_chunk)
                    
                    end_stmt = end_stmt.with_changes(body=build_ast(children[0]))
                    if len(children) == 3: end_stmt = end_stmt.with_changes(orelse=cst.Else(build_ast(children[1])))
                    body.append(end_stmt)
                    
                    visited.remove(join_chunk)
                    curr_chunk = join_chunk
                    
            else:
                # print('build ast for uncond jump sequence')
                
                # does not end in ctrl
                assert len(children) == 1
                curr_chunk = children[0]
        
              
        # end while True
                
        undent()
                        
        block = cst.IndentedBlock(body=body)
        return block
    
    indent()
        
    function: Functional = cfg.func
    entry_chunk = cfg.entry
    body_block = build_ast(entry_chunk) 
    
    undent()   
    
    # TODO make it cleaner todeal with Modles, such as here
    if isinstance(function, cst.Module):
        new_function = function.with_changes(body=body_block.body)
    else:
        new_function = function.with_changes(body=body_block)
    
    # with open("ast_original.txt","w+") as f:
    #     f.writelines(str(function))
    # with open("ast_generated.txt","w+") as f:
    #     f.writelines(str(new_function))
        
    return new_function