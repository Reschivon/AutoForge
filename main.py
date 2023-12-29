
import sys
import ast
import libcst as cst

import autoplag

def viz(ast_tree: cst.Module):
    # from graphviz import Digraph
    
    # dot = Digraph()
    
    # # Define a function to recursively add nodes to the Digraph
    # def add_node(node: cst.CSTNode, parent: cst.CSTNode=None):
        
    #     # Skip
    #     if 'Whitespace' in type(node).__name__ \
    #         or 'Comma' in type(node).__name__ \
    #         or 'EmptyLine' in type(node).__name__:
    #         return
        
    #     # Default type name
    #     node_name = type(node).__name__
        
    #     node_name += '\n' + ast_tree.code_for_node(node).split('\n')[0]
        
    #     # Create node 
    #     dot.node(name=str(id(node)), label=node_name)
        
    #     if parent:
    #         # Link node to parent
    #         dot.edge(str(id(parent)), str(id(node)))
    #     for child in node.children:
    #         # Recurse, provide self as parent
    #         add_node(child, parent=node)

    # # Add nodes to the Digraph
    # add_node(ast_tree)
    
  
    graph = autoplag.DirectedGraph()
    
    def tree_walk(node):
        graph.add_node(node)
        for child in node.children:
            tree_walk(child)
            graph.add_edge(node, child)
        
    tree_walk(ast_tree)
    
    # print(graph.connections)
    
    # print([id(o) for o in graph.objects])
    
    # Render the Digraph as a PNG file
    dot = graph.get_viz(ast_tree)
    # print(dot.source)
    
    dot.format = 'png'
    dot.render('debug/ast_tree')
        
if __name__ == '__main__':
    input_file = sys.argv[1]
    
    print('Reading', input_file)
    
    with open(input_file, "r") as file:
        code = file.read()
        
    ast_tree = cst.parse_module(code)
                
    print('Regenerated:', ast_tree.code, sep='\n')
    
    viz(ast_tree)
    