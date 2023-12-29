def foo(x, y, z):
    
    a = x + y + z * 2
    
    sum = 0
    
    for i in range(a):
        x = y + z
        x *= 1
        
        sum+=x
        
    # if y > 1:
    #     print('here')
        
    # while x > -1:
    #     x -= 1
        
    return sum

def bar():
    print('This is bar!')