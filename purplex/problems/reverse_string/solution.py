def foo(x):
    y = ""
    for i in range(len(x)-1, -1, -1):
        y += x[i]
    return y

print(foo("hello"))
