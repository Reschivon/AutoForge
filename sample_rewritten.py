
import argparse
import autoforge
from autoforge.common_structures import isinstance_Functional
import sys
import libcst as cst
from graphviz import Digraph
from autoforge.printlib import bold, print

def tree_to_graph(ast_tree: cst.Module):
    graph = autoforge.DirectedGraph()
    return graph
    
    def tree_walk(node):
        graph.add_chunk(node)
        for child in node.children:
            tree_walk(child)
            graph.add_edge(node, child)
    tree_walk(ast_tree)
if __name__ == '__main__':
    dot.format = 'png'
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
    dot.render('debug/ast')
    cfgs = autoforge.build_cfgs(ast_tree)
    dot = Digraph()
    for func_node, cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    print()
    dot.render('debug/cfg')
    
    for func_node, cfg in cfgs:
        autoforge.run_rda(cfg, ast_tree, cfgs)
    
    for func_node, cfg in cfgs:
        autoforge.shuffle(cfg, ast_tree)
    dot = Digraph()
    for func_node, cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    print('one')
    print('two')
    dot.render('debug/shuffled_cfg')
    
    for func_node, cfg in reversed(cfgs):
        new_func = autoforge.cfg_to_ast(cfg, ast_tree, remove_comments=True)
        orig_func = cfg.func
        ast_tree = ast_tree.visit(autoforge.Sike(orig_func, new_func))
        
        if isinstance_Functional(orig_func):
            print('generated', orig_func.name.value)
        else:
            print('generated top level code')
    
    with open(args.output, "w") as file:
        file.write(ast_tree.code)
    print('Generated\n', bold(ast_tree.code))