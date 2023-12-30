

from typing import Dict, List, NewType, Set, Optional, Union, Tuple
import typing
import libcst as cst

def isinstance_ControlFlow(node: cst.CSTNode):
    return isinstance(node, cst.If) \
        or isinstance(node, cst.While) \
        or isinstance(node, cst.For)

def get_expression_ControlFlow(node: cst.CSTNode):
    '''
    Get the condition/expression part of a control flow statement
    '''
    if isinstance(node, cst.If): return node.test
    if isinstance(node, cst.While): return node.test
    if isinstance(node, cst.For): return node.iter
 
def isinstance_NonWhitespace(node: cst.CSTNode):
    typename = type(node).__name__
    
    return not ('Whitespace' in typename \
                or 'Comma' in typename \
                or 'EmptyLine' in typename \
                or 'Newline' in typename)

'''
Kept having to use this Union of assignable nodes so I made a meta-type
'''
AssignType = Union[cst.Assign, cst.AugAssign, cst.AnnAssign, cst.CompFor]

def isinstance_AssignType(node: cst.CSTNode):
    return isinstance(node, typing.get_args(AssignType))

def get_assignment_targets(stmt: AssignType) -> Set[str]:
    '''
    Given a cst.CSTNode, if it is any assignment type like `a = b` or `a = b = c` it will return
    all the assigned-to variables as str. 
    
    If there are no assigned-to variables or the node is not an assigment type, then you'll get 
    empty list
    '''
    targets: Set[str] = set()
     
    if isinstance(stmt, cst.Assign):
        for target in stmt.targets:
            targets.add(target.target.value)
            
    elif isinstance(stmt, cst.AugAssign):
        targets.add(stmt.target.value)
        
    elif isinstance(stmt, cst.AnnAssign) and stmt.value:
        targets.add(stmt.target.value)
        
    elif isinstance(stmt, cst.CompFor) and stmt.value:
        targets.add(stmt.target.value)
        
        if stmt.inner_comp_for:
            targets.update(get_assignment_targets(stmt.inner_comp_for))
        
    else:
        return set()
    
    return targets

def first_line(node, ast):
    '''
    First line of code of the node
    Special case: for placeholder nodes, I sometimes just slap in a str instead of initializing 
                  a blank cst.CSTNode properly. In this case this function will just print the string
    Error: If for some reason code is not available on the libCST side, this will print a generic error
    '''
    if isinstance(node, str):
        return node
    
    # Convenient cuz I keep calling this with StmtData instad StmtData.stmt
    if isinstance(node, StmtData):
        node = node.stmt
        
    try:
        return ast.code_for_node(node).strip().split('\n')[0]
    except:
        return 'No code for type ' + type(node).__name__

class StmtData:
    def __init__(self, 
                 stmt: cst.BaseSmallStatement):
        
        self.stmt = stmt
        
        # Chunk index, intra-chunk order, generated during CFG
        # Such that, if statement x executes after y, then order x > y
        # Note the reverse assertion does NOT hold
        self.order: Tuple[int, int] = None
        
        # During RDA
        self.gens: Set[AssignType] = set()
        self.kills: Set[AssignType] = set()
        self.ins: Set[AssignType] = set() 
        self.outs: Set[AssignType] = set()
        self.uses: Set[str] = set()
        
        self.deps: Set[AssignType] = set()
                
class Chunk:
    ''''
    Data object for something loosely resembling BasicBlocks
    
    Holds a list of cst.BaseSmallStatement and corresponding GEN/KILL/IN/OUT sets for the RDA step
    Yes, I know declaring the RDA data here instead of in rda.py isn't good practice but it will
    do for now
    '''
    def __init__(self):
                
        self.stmts: List[StmtData] = []
        
        # Chunk order, see StmtData.order
        self.order: int = None
        
    def append(self, thing: cst.BaseSmallStatement):
        self.stmts.append(StmtData(thing))
        self.stmts[-1].order = (self.order, len(self.stmts) - 1)
            
    def __iter__(self):
        '''
        Iteration defaults to statements only, ignoring in/out sets
        '''
        
        # Note: do not copy the .stmt
        stmts = map(lambda s: s.stmt, self.stmts)
        return stmts.__iter__()
    
    def __getitem__(self, index):
        '''
        Get-index returns all data for a particular statement, including in/out sets
        '''
        return self.stmts[index]
    
    def end_on_unconditional_jump(self) -> bool:
        return len(self.stmts) > 0 and \
              not isinstance_ControlFlow(self.stmts[-1])

class DirectedGraph:
    '''
    Directed Graph implementation for holding Chunk objects 
    
    First insert your Chunks using add_chunk()
    Then inserted Chunks can be linked using add_edge(chunk_parent, chunk_child).
    Edges are ordered by insertion order
    
    call to_image() to generate a graphviz graph.
    
    Can get parents and children of an inserted node
    '''
    def __init__(self):
        self.objects: Dict[int, Chunk] = {}
        self.child_ids: Dict[int, List[int]] = {}
        self.parent_ids: Dict[int, List[int]] = {}
    
    def add_chunk(self, obj):
        # if obj in self.objects:
        #     raise RuntimeError('Cannot add the same object twice')
                
        self.objects[str(id(obj))] = obj
        self.child_ids[str(id(obj))] = list()
        self.parent_ids[str(id(obj))] = list()
        
        return obj
                
    def add_edge(self, parent: cst.CSTNode, child: cst.CSTNode):
        
        assert(id(parent) in self.objects and id(child) in self.objects,
            'Cannot link objects that don\'t exist')
        
        assert(str(id(parent)) in self.child_ids.keys())
        assert(str(id(child)) in self.parent_ids.keys())
        
        self.child_ids[str(id(parent))].append(str(id(child)))
        self.parent_ids[str(id(child))].append(str(id(parent)))
    
    def children(self, obj):
        return list(map(self.objects.get, 
                        self.child_ids[str(id(obj))]
                        ))
    
    def parents(self, obj):
        return list(map(self.objects.get, 
                        self.parent_ids[str(id(obj))]
                        ))
    
    def __iter__(self):
        '''
        Default iteration iterates basic blocks
        '''
        return self.objects.values().__iter__()
        
    def to_image(self, root: cst.Module, dot=None):
        '''
        Makes a graviz representation of the graph, skipping whitespace nodes for brevity
        '''
        from graphviz import Digraph
        
        if dot is None:
            dot = Digraph()
        
        # Keep track of which nodes are being included, so when we add edges later only
        # these are connected
        included_id = set()
        
        for id, node in self.objects.items():
                        
            # Skip whitespace
            if 'Whitespace' in type(node).__name__ \
                or 'Comma' in type(node).__name__ \
                or 'EmptyLine' in type(node).__name__ \
                or 'Newline' in type(node).__name__:
                continue
                        
            if isinstance(node, cst.CSTNode):
                # For single nodes, show the node type and its first line of code
                node_name = type(node).__name__
                
                node_name += '\n' + root.code_for_node(node).split('\n')[0]
            else:
                # For Chunks, iterate over nodes within and print the code for each node
                node_name = '#' + str(node.order) + '\n'
                node_name += ''.join([root.code_for_node(nodelet).strip().split('\n')[0] + '\n' for nodelet in node])
                
            # Create node 
            dot.node(name=id, label=node_name)
            
            included_id.add(id)
            
        # Add edges
        for parent_id, children in self.child_ids.items():       
            for child_id in children:     
                if (parent_id in included_id and child_id in included_id):           
                    dot.edge(parent_id, child_id)
                
        return dot