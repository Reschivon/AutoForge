    
from collections.abc import Collection
from dataclasses import dataclass
from typing import Tuple
import libcst as cst
from builtins import print as OGprint

'''
Dirty thing for quick prints
'''

__indents = 0
def indent():
    global __indents
    __indents += 1
    
    if __indents > 13:
        raise Exception('Indented more than a sane amount! (Is there a bug?)')

def undent():
    global __indents
    __indents -= 1
    
@dataclass
class BoldAnn:
    item: object
    
def bold(thing):
    return BoldAnn(thing)

def stringify(node):
    '''
    First line of code of the node
    Special case: for placeholder nodes, I sometimes just slap in a str instead of initializing 
                  a blank cst.CSTNode properly. In this case this function will just print the string
    Error: If for some reason code is not available on the libCST side, this will print a generic error
    '''
    
    # OGprint("PRINTING", node.__class__.__name__)

    if isinstance(node, str):
        return node
        
    # Convenient cuz I keep calling this with StmtData instad StmtData.stmt
    elif node.__class__.__name__ == 'StmtData':
        return stringify(node.node)
        
    elif isinstance(node, (list, set, dict, tuple)):
        return '(' + ', '.join([stringify(c) for c in node]) + ')'
        
    elif isinstance(node, cst.CSTNode):
        try:
            return cst.parse_module('').code_for_node(node).strip().split('\n')[0]
        except Exception as e:
            return 'No code for node ' + e + node.__class__.__name__
    else:
        return str(node)
    
def iprint(*kwargs):
    global __indents
    indent_str =  '\n' + '    ' * __indents
    
    # OGprint('PREINT REQUESTED', [k for k in kwargs if type(k) == str])
    
    OGprint('    ' * __indents, end='')
    
    for item in kwargs:
        bold = isinstance(item, BoldAnn)
        if bold: 
            OGprint("\033[0;32m", end='')
            item = item.item
        
        strform = stringify(item)
        strform = strform.replace('\n', indent_str)
        OGprint(strform, end=' ')
        
        if bold: OGprint('\033[0m', end='')
    OGprint()
    
def print(*args, **kwargs):
    return iprint(*args, **kwargs)
