"""Native type declarations for ast.py.

This file is only read by Cython at build time; the pure-Python fallback in
ast.py does not need it. Attribute order must match the dataclass field order.
"""

cdef class Span:
    cdef readonly Py_ssize_t start
    cdef readonly Py_ssize_t end


cdef class Node:
    cdef readonly Span span
    cdef readonly str text


cdef class WikiNode(Node):
    cdef readonly tuple children
    cdef readonly object type
    cdef readonly tuple fields


cdef class PrefixNode(Node):
    pass


cdef class TypeNode(Node):
    cdef readonly str name


cdef class EolNode(Node):
    pass


cdef class FieldNode(Node):
    cdef readonly str key
    cdef readonly Span key_span
    cdef readonly object value


cdef class ScalarValueNode(Node):
    cdef readonly str value


cdef class ArrayValueNode(Node):
    cdef readonly tuple children
    cdef readonly tuple items


cdef class ArrayItemNode(Node):
    cdef readonly str name
    cdef readonly str value


cdef class SuffixNode(Node):
    pass


cdef class LeadingNode(Node):
    pass


cdef class TrailingNode(Node):
    pass
