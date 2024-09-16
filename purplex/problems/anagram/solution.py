# determines if a string is an anagram of another string
def foo(a, b):
    return sorted(a.lower()) == sorted(b.lower())
