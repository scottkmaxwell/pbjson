pbjson
======

Packed Binary JSON extension for Python

pbjson is a packed binary JSON encoder and decoder for Python 2.5+
and Python 3.3+.  It is pure Python code with no dependencies,
but includes an optional C extension for a serious speed boost.

pbjson can be used standalone or as an extension to the standard
json module or to simplejson, from which code was heavily borrowed.
The latest documentation for simplejson can be read online here:
http://simplejson.readthedocs.org/

The encoder can be specialized to provide serialization in any kind of
situation, without any special support by the objects to be serialized
(somewhat like pickle). This is best done with the ``default`` kwarg
to dumps.

The decoder can handle incoming JSON strings of any specified encoding
(UTF-8 by default). It can also be specialized to post-process JSON
objects with the ``object_hook`` or ``object_pairs_hook`` kwargs. This
is particularly useful for implementing protocols that have a richer
type system than JSON itself.
