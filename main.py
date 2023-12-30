
import sys
from graphviz import Digraph
import libcst as cst

import autoplag

def tree_to_graph(ast_tree: cst.Module):
    # Convert to graph
    graph = autoplag.DirectedGraph()
    
    def tree_walk(node):
        graph.add_chunk(node)
        for child in node.children:
            tree_walk(child)
            graph.add_edge(node, child)
        
    tree_walk(ast_tree)
    
    return graph
    
if __name__ == '__main__':
    input_file = sys.argv[1]
    
    print('Reading', input_file)
    
    with open(input_file, "r") as file:
        code = file.read()
        
    ast_tree = cst.parse_module(code)
    
    graph = tree_to_graph(ast_tree)
    dot = graph.to_image(ast_tree)    
    dot.format = 'png'
    dot.render('debug/ast')
    
    cfgs = autoplag.build_cfgs(ast_tree)
    
    dot = Digraph()
    for cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    dot.render('debug/cfg')
    
    for cfg in cfgs:
        autoplag.run_rda(cfg, ast_tree)
    
    for cfg in cfgs:
        autoplag.shuffle(cfg, ast_tree)
    
    for cfg in cfgs:
        func = autoplag.add_cfg_to_ast(cfg, ast_tree)  
        print('Generated\n', ast_tree.code_for_node(func))
        
    dot = Digraph()
    for cfg in cfgs:
        cfg.to_image(ast_tree, dot)
    dot.format = 'png'
    dot.render('debug/shuffled_cfg')
    
        