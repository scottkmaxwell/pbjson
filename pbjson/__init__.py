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

from decimal import Decimal

from .scanner import JSONDecodeError as PBJSONDecodeError
from .decoder import PBJSONDecoder
from .encoder import PBJSONEncoder


def _import_c_make_encoder():
    try:
        # noinspection PyUnresolvedReferences
        from . import _speedups
        return _speedups.make_encoder
    except ImportError:
        return None

_default_encoder = PBJSONEncoder(
    skipkeys=False,
    check_circular=True,
    default=None,
    for_json=False,
)


def dump(obj, fp, skipkeys=False, check_circular=True, default=None, sort_keys=False, for_json=False):
    """Serialize ``obj`` as a JSON formatted stream to ``fp`` (a
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
    """Serialize ``obj`` to a JSON formatted ``str``.

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


_default_decoder = PBJSONDecoder(encoding=None, object_hook=None,
                                 object_pairs_hook=None)


def load(fp, encoding=None, cls=None, object_hook=None, parse_float=None,
         parse_int=None, parse_constant=None, object_pairs_hook=None,
         use_decimal=False, namedtuple_as_object=True, tuple_as_array=True,
         **kw):
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a JSON document) to a Python object.

    *encoding* determines the encoding used to interpret any
    :class:`str` objects decoded by this instance (``'utf-8'`` by
    default).  It has no effect when decoding :class:`unicode` objects.

    Note that currently only encodings that are a superset of ASCII work,
    strings of other encodings should be passed in as :class:`unicode`.

    *object_hook*, if specified, will be called with the result of every
    JSON object decoded and its return value will be used in place of the
    given :class:`dict`.  This can be used to provide custom
    deserializations (e.g. to support JSON-RPC class hinting).

    *object_pairs_hook* is an optional function that will be called with
    the result of any object literal decode with an ordered list of pairs.
    The return value of *object_pairs_hook* will be used instead of the
    :class:`dict`.  This feature can be used to implement custom decoders
    that rely on the order that the key and value pairs are decoded (for
    example, :func:`collections.OrderedDict` will remember the order of
    insertion). If *object_hook* is also defined, the *object_pairs_hook*
    takes priority.

    *parse_float*, if specified, will be called with the string of every
    JSON float to be decoded.  By default, this is equivalent to
    ``float(num_str)``. This can be used to use another datatype or parser
    for JSON floats (e.g. :class:`decimal.Decimal`).

    *parse_int*, if specified, will be called with the string of every
    JSON int to be decoded.  By default, this is equivalent to
    ``int(num_str)``.  This can be used to use another datatype or parser
    for JSON integers (e.g. :class:`float`).

    *parse_constant*, if specified, will be called with one of the
    following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
    can be used to raise an exception if invalid JSON numbers are
    encountered.

    If *use_decimal* is true (default: ``False``) then it implies
    parse_float=decimal.Decimal for parity with ``dump``.

    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
    kwarg. NOTE: You should use *object_hook* or *object_pairs_hook* instead
    of subclassing whenever possible.

    """
    return loads(fp.read(),
                 encoding=encoding, cls=cls, object_hook=object_hook,
                 parse_float=parse_float, parse_int=parse_int,
                 parse_constant=parse_constant, object_pairs_hook=object_pairs_hook,
                 use_decimal=use_decimal, **kw)


def loads(s, encoding=None, cls=None, object_hook=None, parse_float=None,
          parse_int=None, parse_constant=None, object_pairs_hook=None,
          use_decimal=False, **kw):
    """Deserialize ``s`` (a ``str`` or ``unicode`` instance containing a JSON
    document) to a Python object.

    *encoding* determines the encoding used to interpret any
    :class:`str` objects decoded by this instance (``'utf-8'`` by
    default).  It has no effect when decoding :class:`unicode` objects.

    Note that currently only encodings that are a superset of ASCII work,
    strings of other encodings should be passed in as :class:`unicode`.

    *object_hook*, if specified, will be called with the result of every
    JSON object decoded and its return value will be used in place of the
    given :class:`dict`.  This can be used to provide custom
    deserializations (e.g. to support JSON-RPC class hinting).

    *object_pairs_hook* is an optional function that will be called with
    the result of any object literal decode with an ordered list of pairs.
    The return value of *object_pairs_hook* will be used instead of the
    :class:`dict`.  This feature can be used to implement custom decoders
    that rely on the order that the key and value pairs are decoded (for
    example, :func:`collections.OrderedDict` will remember the order of
    insertion). If *object_hook* is also defined, the *object_pairs_hook*
    takes priority.

    *parse_float*, if specified, will be called with the string of every
    JSON float to be decoded.  By default, this is equivalent to
    ``float(num_str)``. This can be used to use another datatype or parser
    for JSON floats (e.g. :class:`decimal.Decimal`).

    *parse_int*, if specified, will be called with the string of every
    JSON int to be decoded.  By default, this is equivalent to
    ``int(num_str)``.  This can be used to use another datatype or parser
    for JSON integers (e.g. :class:`float`).

    *parse_constant*, if specified, will be called with one of the
    following strings: ``'-Infinity'``, ``'Infinity'``, ``'NaN'``.  This
    can be used to raise an exception if invalid JSON numbers are
    encountered.

    If *use_decimal* is true (default: ``False``) then it implies
    parse_float=decimal.Decimal for parity with ``dump``.

    To use a custom ``JSONDecoder`` subclass, specify it with the ``cls``
    kwarg. NOTE: You should use *object_hook* or *object_pairs_hook* instead
    of subclassing whenever possible.

    """
    if (cls is None and encoding is None and object_hook is None and
            parse_int is None and parse_float is None and
            parse_constant is None and object_pairs_hook is None
            and not use_decimal and not kw):
        return _default_decoder.decode(s)
    if cls is None:
        cls = PBJSONDecoder
    if object_hook is not None:
        kw['object_hook'] = object_hook
    if object_pairs_hook is not None:
        kw['object_pairs_hook'] = object_pairs_hook
    if parse_float is not None:
        kw['parse_float'] = parse_float
    if parse_int is not None:
        kw['parse_int'] = parse_int
    if parse_constant is not None:
        kw['parse_constant'] = parse_constant
    if use_decimal:
        if parse_float is not None:
            raise TypeError("use_decimal=True implies parse_float=Decimal")
        kw['parse_float'] = Decimal
    return cls(encoding=encoding, **kw).decode(s)


def _toggle_speedups(enabled):
    from . import decoder as dec
    from . import encoder as enc
    from . import scanner as scan
    c_make_encoder = _import_c_make_encoder()
    if enabled:
        dec.scanstring = dec.c_scanstring or dec.py_scanstring
        enc.c_make_encoder = c_make_encoder
        scan.make_scanner = scan.c_make_scanner or scan.py_make_scanner
    else:
        dec.scanstring = dec.py_scanstring
        enc.c_make_encoder = None
        scan.make_scanner = scan.py_make_scanner
    dec.make_scanner = scan.make_scanner
    global _default_decoder
    _default_decoder = PBJSONDecoder(
        encoding=None,
        object_hook=None,
        object_pairs_hook=None,
    )
    global _default_encoder
    _default_encoder = PBJSONEncoder(
        skipkeys=False,
        check_circular=True,
        default=None,
    )


def simple_first(kv):
    """Helper function to pass to item_sort_key to sort simple
    elements to the top, then container elements.
    """
    return isinstance(kv[1], (list, dict, tuple)), kv[0]
