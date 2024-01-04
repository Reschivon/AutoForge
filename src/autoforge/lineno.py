
import libcst as cst
from libcst.metadata import PositionProvider
def embed_line_numbers(ast):
    '''
    There is a metadata interface in libCST that allows us to get line/col positions
    for nodes of a tree, but the interface is locked behind a vistor which makes it
    impossible to get the line number for a given node
    
    So this pass goes through the ast, and adds the new attribute .pos: libcst.metadata.CodeRange
    to all nodes 
    
    Doesn't work since nodes are frozen dataclasses hence new attributes cant be added
    '''
    
    class LineEmbedder(cst.CSTTransformer):
        METADATA_DEPENDENCIES = (PositionProvider,)
        
        def on_leave(self, original_node: cst.CSTNode, updated_node: cst.CSTNode): 
            
            if isinstance(original_node, cst.Module): return True
            
            if self.get_metadata(PositionProvider, original_node):
                pos = self.get_metadata(PositionProvider, original_node)
                
                # print(f"{first_line(node, ast)} found at line {pos.start.line}, column {pos.start.column}")
                
                return updated_node.with_changes(pos=pos)
            
        def on_visit(self, node: cst.CSTNode) -> bool:
            # Only print out names that are parameters
            
            
            return True

    
    # Result is ignored, we do not mutuate the tree strucutre itself, only add attributes to the original
    cst.MetadataWrapper(ast).visit(LineEmbedder())