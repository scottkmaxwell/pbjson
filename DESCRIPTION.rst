pbjson
======

Packed Binary JSON extension for Python

``pbjson`` is a packed binary JSON encoder and decoder for Python 2.5+
and Python 3.3+. It is pure Python code with no dependencies, but
includes an optional C extension for a serious speed boost.

``pbjson`` can be used standalone or as an extension to the standard
``json`` module or to ``simplejson``, from which code was heavily
borrowed. The latest documentation for ``simplejson`` can be read online
here: http://simplejson.readthedocs.org/

The encoder can be specialized to provide serialization in any kind of
situation, without any special support by the objects to be serialized
(somewhat like pickle). This is best done with the ``default`` kwarg to
dumps.

The decoder can handle incoming JSON strings of any specified encoding
(UTF-8 by default). It can also be specialized to post-process JSON
objects with the ``object_hook`` or ``object_pairs_hook`` kwargs. This
is particularly useful for implementing protocols that have a richer
type system than JSON itself.

What is Packed Binary JSON (``PBJSON``)
---------------------------------------

Packed Binary JSON is not the same as ``BSON``. ``BSON`` is a format
used primarily in MongoDB and is meant for efficient parsing. ``PBJSON``
is meant for efficient conversion from a dict or list, transmission and
conversion back to a dict or list on the other end. ``BSON`` has
explicit support for several types not available in standard JSON.
PBJSON supports only those types supported by normal JSON, plus binary
data blobs and set collections.

Unlike ``BSON``, ``PBJSON`` is almost always smaller than the equivalent
JSON. Like ``BSON``, ``PBJSON`` can be very quickly encoded and decoded
since all elements are length encoded.

There are two types of tokens in ``PBJSON``: data and key. Data tokens
can be zero length fundamental types (``false``, ``true``, ``null``),
variable length fundamental types (``int``, ``float``, ``string``,
``binary``) or containers (``set``, ``array``, ``dict``).

The type for the data token is generally stored in the top 3 bits (bits
5-7). Type zero is a special type to represent the zero length
fundamental types. The lower bits indicate the actual value. These are:

Zero-length Data Types:

-  00 - false
-  01 - true
-  02 - null

All other types are variable length. If the length is between 0 and 15,
that length is stored in bits 0-3. For lengths in the 16-2047 range, bit
4 is set and bits 0-2 are combined with the next byte to make an 11-bit
length. If bits 4 and 3 are both set, then the value in bits 0-2 are
combined with the next 2 bytes to create a 19-bit length. However, if
bits 4-0 are all set, this indicates that the following 4 bytes are
simply used as a size. So the token plus length is, one byte (length of
0-15), two bytes (16-2047), three bytes (2048-458751) or five bytes
(458876-4294967295).

Variable-length Data types:

-  2x - int (bytes stored big endian with leading zero bytes removed)
-  4x - negative int (bytes stored big endian as a positive number with
   leading zero bytes removed)
-  6x - float (stored as big endian double precision with trailing zero
   bytes removed)
-  8x - string
-  Ax - binary

Collection types: (length is number of elements)

-  Cx - array
-  Ex - object
-  0C - terminated array
-  0F - terminator

The final entry, the "terminated array" works a bit differently. This is
for use when the length is not known when writing begins. Instead, a
terminator (0F) is written to the stream when the last element of the
array has been written.

Object keys must be text and are a maximum of 127 bytes in length. They
are stored as a (7-bit length, followed by the actual key. The first 128
keys are remembered by index. If the same key is used again, it can be
represented as a single byte consisting of the high bit and the index
number of the key.

In other words, if the recurring key is "toast", it should be encoded as
05 toast. The next time the key "toast" is needed, it can be encoded as
simply 80, since it was the first key.

Here is an example of a simple structure:

.. code:: javascript

   {
       "toast": true,
       "burned": false,
       "name": "the best",
       "toppings": ["jelly","jam","butter"],
       "dimensions": {
           "thickness": 0.7,
           "width": 4.5
       }
   }

::

   E5 05 'toast' 01 06 'burned' 00 04 'name' 88 'the best'
   08 'toppings' C3 85 'jelly' 83 'jam' 86 'butter'
   0A 'dimensions' E2 09 'thickness' 68 3FE6666666666666 05 'width' 62 4012

Let’s break that out:

-  00: E5 - dict with 5 elements
-  01: 05 - key with 5 characters
-  02-06: toast
-  07: 01 - true
-  08: 06 - key with 6 characters
-  09-0E: burned
-  0F: 00 - false
-  10: 04 - key with 4 characters
-  11-14: name
-  15: 88 - string with 8 characters
-  16-1D: the best
-  1E: 08 - key with 8 bytes
-  1F-26: toppings
-  27: C3 - array with 3 elements
-  28: 85 - string with 5 characters
-  29-2D: jelly
-  2E: 83 - string with 3 characters
-  2F-31: jam
-  32: 86 - string with 6 characters
-  33-38: butter
-  39: 0A - key with 10 bytes
-  3A-43: dimensions
-  44: E3 - dict with 2 elements
-  45: 09 - key with 9 characters
-  46-4E: thickness
-  4F: 68 - float with 8 bytes
-  50-57: IEEE representation of .7
-  58: 05 - key with 5 characters
-  59-5D: width
-  5E: 62 - float with 2 bytes
-  5F-60: first 2 bytes of IEEE representation of 4.5. Remaining 6 bytes
   were all zeros.

Total 97 bytes. The tightest ``JSON`` representation requires 126 bytes.
Marshal takes 153 bytes. Pickle takes 184 bytes. BSON takes 145 bytes.

Now here is an example with repeating data:

.. code:: javascript

   {
       "region": 3,
       "countries": [
           {"code": "us", "name": "United States"},
           {"code": "ca", "name": "Canada"},
           {"code": "mx", "name": "Mexico"}
       ]
   }

::

   E2 06 region 21 03 09 countries C3
   E2 04 code 82 us 04 name 8D United States
   E2 82 82 ca 83 86 Canada
   E2 82 82 mx 83 86 Mexico

This breaks down thus:

-  00: E2 - dict with 2 elements
-  01: 06 - key with 6 characters
-  02-07: region
-  08: 21 - int with 1 byte
-  09: 03 - the int for 3. Only a single byte is required.
-  0A: 09 - key with 9 bytes
-  0B-13: countries
-  14: C3 - array with 3 elements
-  15: E2 - dict with 2 elements
-  16: 04 - key with 4 characters
-  17-1A: code
-  19: 82 - string with 2 characters
-  1A-1B: us
-  1C: 04 - key with 4 characters
-  1E-21: name
-  22: 8D - string with 13 characters
-  23-2F: United States
-  30: E2 - dict with 2 elements
-  31: 82 - recurring key 2. Since ‘code’ was the 3rd key, it has an
   index of 2.
-  32: 82 - string with 2 characters
-  33-34: ca
-  35: 83 - recurring key 3
-  36: 86 - string with 6 characters
-  37-3C: Canada
-  3D: E2 - dict with 2 elements
-  3E: 82 - recurring key 0
-  3F: 82 - string with 2 characters
-  40-41: mx
-  42: 83 - recurring key 1
-  43: 86 - string with 6 characters
-  44-49: Mexico

Total 74 bytes. The tightest ``JSON`` representation requires 123 bytes.
Marshal takes 158 bytes and Pickle takes 162. BSON takes 154 bytes.

``Packed Binary JSON`` is available now in the ``pbjson`` Python module.
That module includes a command line utility to convert between normal
``JSON`` files and ``PBJSON``.
