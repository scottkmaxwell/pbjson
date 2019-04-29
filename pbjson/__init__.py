r"""JSON (JavaScript Object Notation) <http://json.org> is a subset of
JavaScript syntax (ECMA-262 3rd edition) used as a lightweight data
interchange format. PBJSON is a binary encoding for JSON.

:mod:`pbjson` exposes an API familiar to users of the standard library
:mod:`marshal` and :mod:`pickle` modules.

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
    >>> pbjson.dumps(2 + 1j, converter=encode_complex)
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
    'PBJSONDecodeError',
]

__author__ = 'Scott Maxwell <scott@codecobblers.com>'

from . import decoder
from . import encoder


def dump(obj, fp, skip_illegal_keys=False, check_circular=True, sort_keys=False, custom=None, convert=None, use_for_json=False):
    """Serialize ``obj`` as a Packed Binary JSON stream to ``fp`` (a
    ``.write()``-supporting file-like object).

    If *skip_illegal_keys* is true then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``)
    will be skipped instead of raising a ``TypeError``.

    If *check_circular* is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If *sort_keys* is true (default: ``False``), the output of dictionaries
    will be sorted by item. *sort_keys* can also be a callable to sort by
    key and/or value.

    *custom* can be an sequence of tuples where each tuple is a type,
    function pair. The function should take an object and return a
    serializable version of the object. A 'custom' token will be output
    to the stream so that the decoder knows the result needs special
    handling.

    *convert(obj)* is a function that should return a serializable version
    of obj or raise ``TypeError``. The default simply raises ``TypeError``.

    If *for_json* is true (default: ``False``), objects with a ``for_json()``
    method will use the return value of that method for encoding as JSON
    instead of the object.

    """
    # cached encoder
    for chunk in encoder.iterencode(obj, skip_illegal_keys, check_circular, sort_keys, custom, convert, use_for_json):
        fp.write(chunk)


def dumps(obj, skip_illegal_keys=False, check_circular=True, sort_keys=False, custom=None, convert=None, use_for_json=False):
    """Serialize ``obj`` to a Packed Binary JSON formatted binary string.

    If *skip_illegal_keys* is false then ``dict`` keys that are not basic types
    (``str``, ``unicode``, ``int``, ``long``, ``float``, ``bool``, ``None``)
    will be skipped instead of raising a ``TypeError``.

    If *check_circular* is false, then the circular reference check
    for container types will be skipped and a circular reference will
    result in an ``OverflowError`` (or worse).

    If *sort_keys* is true (default: ``False``), the output of dictionaries
    will be sorted by item. *sort_keys* can also be a callable to sort by
    key and/or value.

    *custom* can be an sequence of tuples where each tuple is a type,
    function pair. The function should take an object and return a
    serializable version of the object. A 'custom' token will be output
    to the stream so that the decoder knows the result needs special
    handling.

    *convert(obj)* is a function that should return a serializable version
    of obj or raise TypeError. The default simply raises TypeError.

    If *for_json* is true (default: ``False``), objects with a ``for_json()``
    method will use the return value of that method for encoding as JSON
    instead of the object.

    """
    # cached encoder
    return encoder.encode(obj, skip_illegal_keys=skip_illegal_keys, check_circular=check_circular, sort_keys=sort_keys, custom=custom, convert=convert, use_for_json=use_for_json)


def load(fp, document_class=None, float_class=None, custom=None, unicode_errors='strict'):
    """Deserialize ``fp`` (a ``.read()``-supporting file-like object containing
    a Packed Binary JSON document) to a Python object.

        *document_class* allows you to specify an alternate class for objects.
        It will be :class:`dict` if not specified. The class must support __setitem__.

        *float_class* allows you to specify an alternate class for float values
        (e.g. :class:`decimal.Decimal`). The class will be passed a string
         representing the float.
    """
    return decoder.decode(fp.read(), document_class, float_class, custom, unicode_errors)


def loads(s, document_class=None, float_class=None, custom=None, unicode_errors='strict'):
    """Deserialize ``s`` (a binary string containing a Packed
       Binary JSON document) to a Python object.

        *document_class* allows you to specify an alternate class for objects.
        It will be :class:`dict` if not specified. The class must support __setitem__.

        *float_class* allows you to specify an alternate class for float values
        (e.g. :class:`decimal.Decimal`). The class will be passed a string
         representing the float.

    """
    return decoder.decode(s, document_class, float_class, custom, unicode_errors)


def _has_encoder_speedups():
    return bool(encoder.iterencoder is encoder.c_iterencoder)


def _has_decoder_speedups():
    return bool(decoder.decode is decoder.c_decoder)


def _toggle_speedups(enabled):
    if enabled:
        encoder.iterencoder = encoder.c_iterencoder or encoder.py_iterencoder
        decoder.decode = decoder.c_decoder or decoder.py_decoder
    else:
        encoder.iterencoder = encoder.py_iterencoder
        decoder.decode = decoder.py_decoder


def simple_first(kv):
    """Helper function to pass to sort_keys to sort simple
    elements to the top, then container elements.
    """
    return isinstance(kv[1], (list, dict, tuple)), kv[0]
