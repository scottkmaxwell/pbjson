r"""JSON (JavaScript Object Notation) <http://json.org> is a subset of
JavaScript syntax (ECMA-262 3rd edition) used as a lightweight data
interchange format.

:mod:`simplejson` exposes an API familiar to users of the standard library
:mod:`marshal` and :mod:`pickle` modules. It is the externally maintained
version of the :mod:`json` library contained in Python 2.6, but maintains
compatibility with Python 2.4 and Python 2.5 and (currently) has
significant performance advantages, even without using the optional C
extension for speedups.

Encoding basic Python object hierarchies::

    >>> import pbjson
    >>> pbjson.dumps(['foo', {'bar': ('baz', None, 1.0, 2)}])
    b'\xc2\x83foo\xe1\x03bar\xc4\x83baz\x02b?\xf0!\x02'
    >>> print(pbjson.dumps(u'\u1234'))
    b'\x83\xe1\x88\xb4'
    >>> print(pbjson.dumps('\\'))
    b'\x81\\'
    >>> print(pbjson.dumps({"c": 0, "b": 0, "a": 0}, sort_keys=True))
    '\xe3\x01a \x01b \x01c '
    >>> from pbjson.compat import BytesIO
    >>> io = BytesIO()
    >>> pbjson.dump(['streaming API'], io)
    >>> io.getvalue()
    '["streaming API"]'

Decoding PBJSON::

    >>> import pbjson
    >>> obj = [u'foo', {u'bar': [u'baz', None, 1.0, 2]}]
    >>> pbjson.loads('["foo", {"bar":["baz", null, 1.0, 2]}]') == obj
    True
    >>> pbjson.loads('"\\"foo\\bar"') == u'"foo\x08ar'
    True
    >>> from pbjson.compat import StringIO
    >>> io = StringIO('["streaming API"]')
    >>> pbjson.load(io)[0] == 'streaming API'
    True

Specializing JSON object decoding::

    >>> import pbjson
    >>> def as_complex(dct):
    ...     if '__complex__' in dct:
    ...         return complex(dct['real'], dct['imag'])
    ...     return dct
    ...
    >>> pbjson.loads('{"__complex__": true, "real": 1, "imag": 2}',
    ...     object_hook=as_complex)
    (1+2j)
    >>> from decimal import Decimal
    >>> pbjson.loads('1.1', parse_float=Decimal) == Decimal('1.1')
    True

Specializing JSON object encoding::

    >>> import pbjson
    >>> def encode_complex(obj):
    ...     if isinstance(obj, complex):
    ...         return [obj.real, obj.imag]
    ...     raise TypeError(repr(o) + " is not JSON serializable")
    ...
    >>> pbjson.dumps(2 + 1j, default=encode_complex)
    '[2.0, 1.0]'
    >>> pbjson.PBJSONEncoder(default=encode_complex).encode(2 + 1j)
    '[2.0, 1.0]'
    >>> ''.join(pbjson.PBJSONEncoder(default=encode_complex).iterencode(2 + 1j))
    '[2.0, 1.0]'


Using pbjson.tool from the shell to validate and pretty-print::

    $ echo '{"json":"obj"}' | python -m simplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -m simplejson.tool
    Expecting property name: line 1 column 3 (char 2)
"""
from __future__ import absolute_import
__version__ = '1.0.0'
__all__ = [
    'dump', 'dumps', 'load', 'loads',
    'PBJSONDecoder', 'PBJSONDecodeError', 'PBJSONEncoder',
]

__author__ = 'Scott Maxwell <scott@codecobblers.com>'

from .decoder import decode
from .encoder import PBJSONEncoder


def _import_c_make_encoder():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.make_encoder
    except ImportError:
        return None

_default_encoder = PBJSONEncoder()


def dump(obj, fp, skipkeys=False, check_circular=True, default=None, sort_keys=False, for_json=False):
    """Serialize ``obj`` as a Packed Binary JSON stream to ``fp`` (a
    ``.write()``-supporting file-like object).

    If *skipkeys* is true then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``)
    will be skipped instead of raising a ``TypeError``.

    If *check_circular* is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    *default(obj)* is a function that should return a serializable version
    of obj or raise ``TypeError``. The default simply raises ``TypeError``.

    If *sort_keys* is true (default: ``False``), the output of dictionaries
    will be sorted by item. *sort_keys* can also be a callable to sort by
    key and/or value.

    If *for_json* is true (default: ``False``), objects with a ``for_json()``
    method will use the return value of that method for encoding as JSON
    instead of the object.

    """
    # cached encoder
    if not skipkeys and check_circular and default is None and not for_json:
        iterable = _default_encoder.iterencode(obj)
    else:
        iterable = PBJSONEncoder(skipkeys=skipkeys, check_circular=check_circular, default=default, sort_keys=sort_keys, for_json=for_json).iterencode(obj)
    # could accelerate with writelines in some versions of Python, at
    # a debuggability cost
    for chunk in iterable:
        fp.write(chunk)


def dumps(obj, skipkeys=False, check_circular=True, default=None, sort_keys=False, for_json=False):
    """Serialize ``obj`` to a Packed Binary JSON formatted binary string.

    If ``skipkeys`` is false then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``)
    will be skipped instead of raising a ``TypeError``.

    If ``check_circular`` is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    ``default(obj)`` is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    If *sort_keys* is true (default: ``False``), the output of dictionaries
    will be sorted by item. *sort_keys* can also be a callable to sort by
    key and/or value.

    If *for_json* is true (default: ``False``), objects with a ``for_json()``
    method will use the return value of that method for encoding as JSON
    instead of the object.

    """
    # cached encoder
    if not skipkeys and check_circular and default is None and not sort_keys and not for_json:
        return _default_encoder.encode(obj)
    return PBJSONEncoder(skipkeys=skipkeys, check_circular=check_circular, default=default, sort_keys=sort_keys, for_json=for_json).encode(obj)


def load(fp, document_class=None, float_class=None):
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a Packed Binary JSON document) to a Python object.

        *document_class* allows you to specify an alternate class for objects.
        It will be :class:`dict` if not specified. The class must support __setitem__.

        *float_class* allows you to specify an alternate class for float values
        (e.g. :class:`decimal.Decimal`). The class will be passed a string
         representing the float.
    """
    return decode(fp.read(), document_class, float_class)


def loads(s, document_class=None, float_class=None):
    """Deserialize ``s`` (a binary string containing a Packed
       Binary JSON document) to a Python object.

        *document_class* allows you to specify an alternate class for objects.
        It will be :class:`dict` if not specified. The class must support __setitem__.

        *float_class* allows you to specify an alternate class for float values
        (e.g. :class:`decimal.Decimal`). The class will be passed a string
         representing the float.

    """
    return decode(s, document_class, float_class)


def _toggle_speedups(enabled):
    from . import decoder as dec
    from . import encoder as enc
    c_make_encoder = _import_c_make_encoder()
    if enabled:
        enc.c_make_encoder = c_make_encoder
    else:
        enc.c_make_encoder = None
    global _default_encoder
    _default_encoder = PBJSONEncoder()


def simple_first(kv):
    """Helper function to pass to sort_keys to sort simple
    elements to the top, then container elements.
    """
    return isinstance(kv[1], (list, dict, tuple)), kv[0]
