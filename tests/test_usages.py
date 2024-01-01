
import libcst as cst
from autoplag.rda import get_all_usages
      
test = [
    'x', ['x'],
    'x.y.z', ['x.y.z'],
    'hi.go()', ['hi', 'go'],
    'a = b', ['b'],
    'for i in range(x): pass', ['range', 'x'],
    'if b: print(o)', ['b'],
    'Glizzy(g)', ['Glizzy', 'g'],
]

def testa(code, expected):
    ast = cst.parse_module(code)
    assert get_all_usages(ast) == expected, \
        'Got ' + str(get_all_usages(ast)) + ' expected ' + str(expected)
    print('    Success')
    
if __name__ == "__main__":
    for a, b in zip(test[:-1:2], test[1::2]):
        print('test', a, b)
        testa(a, b)