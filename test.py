def foo(x, y, z):
    
    a = x + y + z * 2
    
    sum = 0
    
    for i in range(a):
        x = y + z
        x *= 1
        
        sum+=x
        
    return sum