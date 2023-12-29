
from typing import Dict, List, Set
import libcst as cst

class DirectedGraph:
    
    def __init__(self):
        self.connections: Dict[int, Set[int]] = {}
        self.objects: Dict[int, cst.CSTNode] = {}
    
    def add_node(self, obj):
        if obj in self.objects:
            raise RuntimeError('Cannot add the same object twice')
                
        self.objects[str(id(obj))] = obj
        self.connections[str(id(obj))] = set()
                
    def add_edge(self, parent: cst.CSTNode, child: cst.CSTNode):
        
        assert(id(parent) in self.objects and id(child) in self.objects,
            'Cannot link objects that don\'t exist')
        
        assert(str(id(parent)) in self.connections)
        
        self.connections[str(id(parent))].add(str(id(child)))
    
    def get_viz(self, root: cst.Module):
        from graphviz import Digraph
        
        dot = Digraph()
        
        included_id = set()
        
        for id, node in self.objects.items():
                        
            # Skip
            if 'Whitespace' in type(node).__name__ \
                or 'Comma' in type(node).__name__ \
                or 'EmptyLine' in type(node).__name__:
                continue
            
            # Default type name
            node_name = type(node).__name__
            
            node_name += '\n' + root.code_for_node(node).split('\n')[0]
            
            # Create node 
            dot.node(name=id, label=node_name)
            
            included_id.add(id)
            
        for parent_id, children in self.connections.items():       
            for child_id in children:     
                if (parent_id in included_id and child_id in included_id):           
                    dot.edge(parent_id, child_id)
                
        return dot