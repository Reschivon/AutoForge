
import sys
import ast
import libcst as cst

import autoplag

def tree_to_graph(ast_tree: cst.Module):
    # Convert to graph
    graph = autoplag.DirectedGraph()
    
    def tree_walk(node):
        graph.add_node(node)
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
    
    print('Regenerated:', ast_tree.code, sep='\n')
    
    graph = tree_to_graph(ast_tree)
    dot = graph.to_image(ast_tree)    
    dot.format = 'png'
    dot.render('debug/ast')
    
    cfg = autoplag.build_cfg(ast_tree)
    
    dot = cfg.to_image(ast_tree)
    dot.format = 'png'
    dot.render('debug/cfg')
    
    autoplag.rda(cfg, ast_tree)
        