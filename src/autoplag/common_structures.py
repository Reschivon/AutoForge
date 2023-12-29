

from typing import Dict, List, NewType, Set, Optional, Union, Tuple
import libcst as cst

def isinstance_ControlFlow(node: cst.CSTNode):
    return isinstance(node, cst.If) \
        or isinstance(node, cst.While) \
        or isinstance(node, cst.For)
 
def isinstance_NonWhitespace(node: cst.CSTNode):
    typename = type(node).__name__
    
    return not ('Whitespace' in typename \
                or 'Comma' in typename \
                or 'EmptyLine' in typename \
                or 'Newline' in typename)

AssignType = Union[cst.Assign, cst.AugAssign, cst.AnnAssign]

def get_assignment_targets(stmt: AssignType) -> Set[str]:
    targets: Set[str] = set()
     
    if isinstance(stmt, cst.Assign):
        for target in stmt.targets:
            targets.add(target.target.value)
            
    elif isinstance(stmt, cst.AugAssign):
        targets.add(stmt.target.value)
        
    elif isinstance(stmt, cst.AnnAssign) and stmt.value:
        targets.add(stmt.target.value)
        
    else:
        return set()
    
    return targets

class StmtData:
    def __init__(self, 
                 stmt: cst.BaseSmallStatement):
        
        self.stmt = stmt
        self.gens: Set[AssignType] = set()
        self.kills: Set[Tuple[str, AssignType]] = set()
        self.ins: Set[AssignType] = set() 
        self.outs: Set[AssignType] = set()
        
class Chunk:
    def __init__(self):
                
        self.stmts: List[StmtData] = []
        
    def append(self, thing: cst.BaseSmallStatement):
        self.stmts.append(StmtData(thing))
            
    def __iter__(self):
        '''
        Iterate statements only, not gen kill sets
        '''
        
        # Note: do not copy
        stmts = map(lambda s: s.stmt, self.stmts)
        return stmts.__iter__()
    
    def end_on_unconditional_jump(self) -> bool:
        return len(self.stmts) > 0 and \
              not isinstance_ControlFlow(self.stmts[-1])

class DirectedGraph:
    
    def __init__(self):
        self.connections: Dict[int, Set[int]] = {}
        self.objects: Dict[int, Chunk] = {}
    
    def add_node(self, obj):
        # if obj in self.objects:
        #     raise RuntimeError('Cannot add the same object twice')
                
        self.objects[str(id(obj))] = obj
        self.connections[str(id(obj))] = set()
        
        return obj
                
    def add_edge(self, parent: cst.CSTNode, child: cst.CSTNode):
        
        assert(id(parent) in self.objects and id(child) in self.objects,
            'Cannot link objects that don\'t exist')
        
        assert(str(id(parent)) in self.connections)
        
        self.connections[str(id(parent))].add(str(id(child)))
    
    def children(self, obj):
        return map(self.objects.get, self.connections(str(id(obj))))
    
    def parents(self, obj):
        # TODO make faster
        parent_ids = []
        for parent, children in self.connections:
            if str(id(obj)) in children:
                parent_ids.append(self.objects[parent]) 
        return parent_ids
        
    def to_image(self, root: cst.Module):
        from graphviz import Digraph
        
        dot = Digraph()
        
        included_id = set()
        
        for id, node in self.objects.items():
                        
            # Skip
            if 'Whitespace' in type(node).__name__ \
                or 'Comma' in type(node).__name__ \
                or 'EmptyLine' in type(node).__name__ \
                or 'Newline' in type(node).__name__:
                continue
            
            # Default type name
            if isinstance(node, cst.CSTNode):
                node_name = type(node).__name__
                
                node_name += '\n' + root.code_for_node(node).split('\n')[0]
            else:
                node_name = ''.join([root.code_for_node(nodelet).strip().split('\n')[0] + '\n' for nodelet in node])
                
            # Create node 
            dot.node(name=id, label=node_name)
            
            included_id.add(id)
            
        for parent_id, children in self.connections.items():       
            for child_id in children:     
                if (parent_id in included_id and child_id in included_id):           
                    dot.edge(parent_id, child_id)
                
        return dot