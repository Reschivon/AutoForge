
import libcst as cst
from autoforge.rda import get_usages, get_assignments
      
uses_answers = [
    'x', ['x'],
    'x.y.z', ['x.y.z'],
    'hi.go()', ['hi'],
    'hi.foo.go()', ['hi.foo'],
    'a = b', ['b'],
    'for i in range(x): pass', ['range', 'x'],
    '[print("lol") for i in range(x)]', ['print', 'range', 'x'],
    'if b: print(o)', ['b'], # Note: skip control flow body
    'Glizzy(g)', ['Glizzy', 'g'],
    '[beliefs for i, beliefs in enumerate(self.ghostBeliefs) if livingGhosts[i + 1]]', ['enumerate', 'self.ghostBeliefs', 'livingGhosts']
]

def test_uses(code, expected):
    ast = cst.parse_module(code)
    assert get_usages(ast) == set(expected), \
        'Got ' + str(get_usages(ast)) + ' expected ' + str(expected)
    print('    Success')
   
def test_assign(code, expected):
    ast = cst.parse_module(code)
    assert get_assignments(ast) == set(expected), \
        'Got ' + str(get_assignments(ast)) + ' expected ' + str(expected)
    print('    Success')
    
    
assign_answers = [
    'x = y', ['x'],
    'x.y.z = y', ['x.y.z'],
    'hi.go()', ['hi'],
    'hi.foo.go()', ['hi.foo'],
    'for i in range(x): pass', ['i'],
    '[print("lol") for i in range(x)]', [],  # No persisting assignments, since 'i' is scoped to the comprehension
    'if b: print(o)', [], # Note: skip control flow body
    'Glizzy(g)', [], # TODO Assume no args mutation for now
    '[beliefs for i, beliefs in enumerate(self.ghostBeliefs) if livingGhosts[i + 1]]', [],
]

if __name__ == "__main__":
    for a, b in zip(uses_answers[:-1:2], uses_answers[1::2]):
        print('test', a, b)
        test_uses(a, b)
        
    for a, b in zip(assign_answers[:-1:2], assign_answers[1::2]):
        print('test', a, b)
        test_assign(a, b)