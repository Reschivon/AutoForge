
import sys
from graphviz import Digraph
import libcst as cst
import argparse

import autoforge
from autoforge.common_structures import isinstance_Functional
from autoforge.printlib import bold, print

def tree_to_graph(ast_tree: cst.Module):
    # Convert to graph
    graph = autoforge.DirectedGraph()
    
    def tree_walk(node):
        graph.add_chunk(node)
        for child in node.children:
            tree_walk(child)
            graph.add_edge(node, child)
        
    tree_walk(ast_tree)
    
    return graph
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("-i", "--input", help="Input file", required=True)
    parser.add_argument("-o", "--output", help="Output file", required=True)
    args = parser.parse_args()
    
    print('Reading', args.input)
    
    with open(args.input, "r") as file:
        code = file.read()
        
    ast_tree = cst.parse_module(code)
    
    graph = tree_to_graph(ast_tree)
    dot = graph.to_image(ast_tree)    
    dot.format = 'png'
    dot.render('debug/ast')
    
    cfgs = autoforge.build_cfgs(ast_tree)
    
    dot = Digraph()
    for func_node, cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    dot.render('debug/cfg')
    
    # CFGS are listed in nesting order, with smaller functions first. Parent functions may define
    # variables that are used as captures in nested function, so we do rda on nested ones first, and
    # save captures captured to cfg.captures. Then the parent can read this
    print()
    
    for func_node, cfg in cfgs:
        autoforge.run_rda(cfg, ast_tree, cfgs)
    
    for func_node, cfg in cfgs:
        autoforge.shuffle(cfg, ast_tree)
    
    dot = Digraph()
    for func_node, cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    dot.render('debug/shuffled_cfg')
    
    # CFGS are listed in nesting order, with smaller functions first. We replace the LARGEST functions
    # before the smaller ones, hence the reversed iteration. This is because, if we swap the smaller
    # function before the parent one, it'll eventually get overwritten by the parent's (old) copy 
    # of the nested function
    print('one')
    print('two')
    
    for func_node, cfg in reversed(cfgs):
        orig_func = cfg.func
        
        new_func = autoforge.cfg_to_ast(cfg, ast_tree, remove_comments=True)  
        
        ast_tree = ast_tree.visit(autoforge.Sike(orig_func, new_func))
        
        if isinstance_Functional(orig_func):
            # print("new func", new_func)
            print('generated', orig_func.name.value) #, '\n', ast_tree.code_for_node(new_func))
        else:
            print('generated top level code')
        
    print('Generated\n', bold(ast_tree.code))
    
    with open(args.output, "w") as file:
        file.write(ast_tree.code)