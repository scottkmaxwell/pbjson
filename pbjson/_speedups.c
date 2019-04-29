/* -*- mode: C; c-file-style: "python"; c-basic-offset: 4 -*- */
#include "Python.h"
#include "structmember.h"
#include <math.h>

#if PY_MAJOR_VERSION >= 3
#define PyString_Check PyBytes_Check
#define PyString_GET_SIZE PyBytes_GET_SIZE
#define PyString_AS_STRING PyBytes_AS_STRING
#define PyString_FromStringAndSize PyBytes_FromStringAndSize
#define _PyString_Resize _PyBytes_Resize
#else /* PY_MAJOR_VERSION >= 3 */
#endif /* PY_MAJOR_VERSION < 3 */

#define Enc_FALSE 0
#define Enc_TRUE 1
#define Enc_NULL 2
#define Enc_INF 3
#define Enc_NEGINF 4
#define Enc_NAN 5
#define Enc_TERMINATED_LIST 0xc
#define Enc_CUSTOM 0xe
#define Enc_TERMINATOR 0xf
#define Enc_INT 0x20
#define Enc_NEGINT 0x40
#define Enc_FLOAT 0x60
#define Enc_STRING 0x80
#define Enc_BINARY 0xA0
#define Enc_LIST 0xC0
#define Enc_DICT 0xE0

#define FltEnc_Plus 0xa
#define FltEnc_Minus 0xb
#define FltEnc_Decimal 0xd
#define FltEnc_E 0xe

#define BUFFER_SIZE 0x1000

#if PY_VERSION_HEX < 0x02070000
#if !defined(PyOS_string_to_double)
#define PyOS_string_to_double json_PyOS_string_to_double
static double
json_PyOS_string_to_double(const char *s, char **endptr, PyObject *overflow_exception);
static double
json_PyOS_string_to_double(const char *s, char **endptr, PyObject *overflow_exception)
{
    double x;
    assert(endptr == NULL);
    assert(overflow_exception == NULL);
    PyFPE_START_PROTECT("json_PyOS_string_to_double", return -1.0;)
    x = PyOS_ascii_atof(s);
    PyFPE_END_PROTECT(x)
    return x;
}
#endif
#endif /* PY_VERSION_HEX < 0x02070000 */

#if PY_VERSION_HEX < 0x02060000
#if !defined(Py_TYPE)
#define Py_TYPE(ob)     (((PyObject*)(ob))->ob_type)
#endif
#if !defined(Py_SIZE)
#define Py_SIZE(ob)     (((PyVarObject*)(ob))->ob_size)
#endif
#if !defined(PyVarObject_HEAD_INIT)
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif
#endif /* PY_VERSION_HEX < 0x02060000 */

#if PY_VERSION_HEX < 0x02050000
#if !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif
#if !defined(Py_IS_FINITE)
#define Py_IS_FINITE(X) (!Py_IS_INFINITY(X) && !Py_IS_NAN(X))
#endif
#endif /* PY_VERSION_HEX < 0x02050000 */

#ifdef __GNUC__
#define UNUSED __attribute__((__unused__))
#else
#define UNUSED
#endif


typedef struct _PyEncoder {
    PyObject *defaultfn;
    PyObject *custom;
    PyObject *Decimal;
    PyObject *Mapping;

    PyObject *item_sort_kw;
    PyObject *markers;      /* Dict for tracking circular references */
    PyObject *key_memo;     /* Place to keep track of previously used keys */
    PyObject *chunk_list;   /* A list of previously accumulated strings */
    PyObject *buffer;       /* A string for building up a chunk */
    unsigned char* ptr;     /* Pointer into the buffer */
    int position;           /* How far into the buffer we have written */

    int check_circular;
    int skipkeys;
    int for_json;
    int single_custom;

} PyEncoder;

typedef struct _PyDecoder {
    PyObject *document_class;
    PyObject *float_class;
    PyObject *custom;
    PyObject *keys;
    const unsigned char* data;
    const char* unicode_errors;
    int len;
} PyDecoder;


static int
JSON_Accu_Accumulate(PyEncoder *acc, const unsigned char *bytes, size_t len);
static PyObject *
JSON_Accu_FinishAsList(PyEncoder *acc);
static void
JSON_Accu_Destroy(PyEncoder *acc);

static PyObject *
decode_one(PyDecoder *decoder);
#if PY_MAJOR_VERSION < 3
static PyObject *
join_list_string(PyObject *lst);
#else
static PyObject *
join_list_bytes(PyObject *lst);
#endif
static int
encode_list(PyEncoder *encoder, PyObject *seq);
static int
encode_terminated_list(PyEncoder *encoder, PyObject *iter);
static int
encode_one(PyEncoder *encoder, PyObject *obj);
static int
encode_dict(PyEncoder *encoder, PyObject *dct);
static PyObject *
encode_dict_items(PyEncoder *encoder, PyObject *dct);
static void
raise_errmsg(const char *msg);
static int
_is_namedtuple(PyObject *obj);
static int
_has_for_json_hook(PyObject *obj);
static PyObject *
moduleinit(void);


static void
raise_errmsg(const char *msg)
{
    /* Use JSONDecodeError exception to raise a nice looking ValueError subclass */
    static PyObject *PBJSONDecodeError = NULL;
    PyObject *exc;
    if (PBJSONDecodeError == NULL) {
        PyObject *scanner = PyImport_ImportModule("pbjson.decoder");
        if (scanner == NULL)
            return;
        PBJSONDecodeError = PyObject_GetAttrString(scanner, "PBJSONDecodeError");
        Py_DECREF(scanner);
        if (PBJSONDecodeError == NULL)
            return;
    }
    exc = PyObject_CallFunction(PBJSONDecodeError, "(z)", msg);
    if (exc) {
        PyErr_SetObject(PBJSONDecodeError, exc);
        Py_DECREF(exc);
    }
}

#if PY_MAJOR_VERSION >= 3
static PyObject *
join_list_bytes(PyObject *lst)
{
    /* return u''.join(lst) */
    static PyObject *joinfn = NULL;
    if (joinfn == NULL) {
        PyObject *ustr = PyString_FromStringAndSize(NULL, 0);
        if (ustr == NULL)
            return NULL;

        joinfn = PyObject_GetAttrString(ustr, "join");
        Py_DECREF(ustr);
        if (joinfn == NULL)
            return NULL;
    }
    return PyObject_CallFunctionObjArgs(joinfn, lst, NULL);
}
#else /* PY_MAJOR_VERSION >= 3 */
static PyObject *
join_list_string(PyObject *lst)
{
    /* return ''.join(lst) */
    static PyObject *joinfn = NULL;
    if (joinfn == NULL) {
        PyObject *ustr = PyString_FromStringAndSize(NULL, 0);
        if (ustr == NULL)
            return NULL;

        joinfn = PyObject_GetAttrString(ustr, "join");
        Py_DECREF(ustr);
        if (joinfn == NULL)
            return NULL;
    }
    return PyObject_CallFunctionObjArgs(joinfn, lst, NULL);
}
#endif /* PY_MAJOR_VERSION < 3 */


static char inf_string_be[8] = {0x7f, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
static char neginf_string_be[8] = {0xff, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
static char nan_string_be[8] = {0x7f, 0xf8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
static char inf_string_le[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf0, 0x7f};
static char neginf_string_le[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf0, 0xff};
static char nan_string_le[8] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf8, 0x7f};
static double inf_value = 0.0;
static double neginf_value = 0.0;
static double nan_value = 0.0;
static int endian = 0;

static void fix_special_floats()
{
    endian = 1;
    if (((const char*)&endian)[0]) {
        memcpy(&inf_value, inf_string_le, 8);
        memcpy(&neginf_value, neginf_string_le, 8);
        memcpy(&nan_value, nan_string_le, 8);
    } else {
        memcpy(&inf_value, inf_string_be, 8);
        memcpy(&neginf_value, neginf_string_be, 8);
        memcpy(&nan_value, nan_string_be, 8);
    }
}

static void
set_overflow()
{
    raise_errmsg("Invalid binary stream for Packed Binary JSON");
}

static PyObject *
decode_unsigned_long_long(PyDecoder *decoder, int length)
{
    unsigned long long accumulator = *decoder->data++;
    decoder->len--;
    length--;
    while (length) {
        accumulator <<= 8;
        accumulator |= *decoder->data++;
        decoder->len--;
        length--;
    }
    return PyLong_FromUnsignedLongLong(accumulator);
}

static PyObject *
decode_int(PyDecoder *decoder, int length)
{
    int one_bite = length<=8 ? length : 8;
    if (!one_bite) {
        return PyLong_FromLong(0);
    }
    PyObject *tmp = NULL;
    PyObject *more = NULL;
    PyObject *shifter = NULL;
    PyObject *result = decode_unsigned_long_long(decoder, one_bite);
    while (length > 8) {
        length -= 8;
        one_bite = length<=8 ? length : 8;
        if (!shifter) {
            shifter = PyLong_FromLong(one_bite << 3);
        }
        else if (length < 8) {
            Py_XDECREF(shifter);
            shifter = PyLong_FromLong(length << 3);
        }
        tmp = PyNumber_InPlaceLshift(result, shifter);
        Py_DECREF(result);
        result = tmp;
        more = decode_unsigned_long_long(decoder, one_bite);
        tmp = PyNumber_InPlaceOr(result, more);
        Py_DECREF(result);
        result = tmp;
        Py_XDECREF(more);
    }
    Py_XDECREF(shifter);
    return result;
}

static PyObject *
decode_negint(PyDecoder *decoder, int length)
{
    PyObject *result = decode_int(decoder, length);
    if (result) {
        PyObject *inverted = PyNumber_Negative(result);
        Py_DECREF(result);
        result = inverted;
    }
    return result;
}

static char
nibble(unsigned char c)
{
    if (c <= 9)
        return c | '0';
    if (c == FltEnc_Plus) {
        return '+';
    }
    if (c == FltEnc_Minus) {
        return '-';
    }
    if (c == FltEnc_Decimal) {
        return '.';
    }
    if (c == FltEnc_E) {
        return 'e';
    }
    return 0;
}

static PyObject *
decode_float(PyDecoder *decoder, int length)
{
    char buffer[0x40];
    if (length > 0x1f) {
        set_overflow();
        return NULL;
    }
    int unpacked_len = 0;
    if (!length) {
        buffer[0] = '0';
        ++unpacked_len;
    }
    while (length) {
        unsigned char c = *decoder->data++;
        decoder->len--;
        buffer[unpacked_len++] = nibble(c>>4);
        buffer[unpacked_len++] = nibble(c & 0xf);
        length--;
    }
    if (buffer[unpacked_len-1] == '.') {
        unpacked_len--;
    }
    buffer[unpacked_len] = 0;
    if (!decoder->float_class) {
        double d = PyOS_string_to_double(buffer, NULL, NULL);
        if (d == -1.0 && PyErr_Occurred())
            return NULL;
        return PyFloat_FromDouble(d);
    }
    PyObject *numstr = PyUnicode_FromStringAndSize(buffer, unpacked_len);
    PyObject *result = PyObject_CallFunctionObjArgs(decoder->float_class, numstr, NULL);
    Py_XDECREF(numstr);
    return result;
}

static PyObject *
decode_special_float(PyDecoder *decoder, unsigned char token)
{
    if (!endian) {
        fix_special_floats();
    }
    if (!decoder->float_class) {
        double d = token == Enc_INF ? inf_value : token == Enc_NEGINF ? neginf_value : nan_value;
        return PyFloat_FromDouble(d);
    }
    const char *str = token == Enc_INF ? "inf" : token == Enc_NEGINF ? "-inf" : "nan";
    PyObject *numstr = PyUnicode_FromStringAndSize(str, token == Enc_NEGINF ? 4 : 3);
    PyObject *result = PyObject_CallFunctionObjArgs(decoder->float_class, numstr, NULL);
    Py_XDECREF(numstr);
    return result;
}

static PyObject *
decode_string(PyDecoder *decoder, int length)
{
    PyObject *result = PyUnicode_DecodeUTF8((const char *)decoder->data, length, decoder->unicode_errors);
    decoder->data += length;
    decoder->len -= length;
    return result;
}

static PyObject *
decode_binary(PyDecoder *decoder, int length)
{
    PyObject *result = PyBytes_FromStringAndSize((const char *)decoder->data, length);
    decoder->data += length;
    decoder->len -= length;
    return result;
}

static PyObject *
decode_list(PyDecoder *decoder, int length)
{
    PyObject *result = PyList_New(0);
    if (result) {
        while (length) {
            if (length == -1) {
                if (*decoder->data == Enc_TERMINATOR) {
                    decoder->data++;
                    decoder->len--;
                    break;
                }
            } else {
                --length;
            }
            PyObject *obj = decode_one(decoder);
            if (!obj) {
                Py_CLEAR(result);
                break;
            }
            if (PyList_Append(result, obj)) {
                Py_XDECREF(obj);
                Py_CLEAR(result);
                break;
            }
            Py_XDECREF(obj);
        }
    }
    return result;
}

static PyObject *
decode_dict(PyDecoder *decoder, int length)
{
    PyObject *result = NULL;
    if (decoder->document_class) {
        result = PyObject_CallFunctionObjArgs(decoder->document_class, NULL);
    }
    else {
        result = PyDict_New();
    }
    if (result) {
        PyObject *key;
        while (length) {
            if (decoder->len < 2) {
                set_overflow();
                Py_CLEAR(result);
                break;
            }
            if (length == -1) {
                if (*decoder->data == Enc_TERMINATOR) {
                    decoder->data++;
                    decoder->len--;
                    break;
                }
            } else {
                --length;
            }
            unsigned char token = *decoder->data++;
            decoder->len--;
            if (token & 0x80) {
                if (!decoder->keys) {
                    Py_CLEAR(result);
                    set_overflow();
                    break;
                }
                key = PyList_GetItem(decoder->keys, token & 0x7f);
                if (!key) {
                    Py_CLEAR(result);
                    break;
                }
                Py_INCREF(key);
            }
            else {
                if (token > decoder->len) {
                    Py_CLEAR(result);
                    set_overflow();
                    break;
                }
                key = PyUnicode_FromStringAndSize((const char *)decoder->data, token);
                if (!key) {
                    Py_CLEAR(result);
                    break;
                }
                decoder->data += token;
                decoder->len -= token;
                if (!decoder->keys) {
                    decoder->keys = PyList_New(0);
                }
                if (!decoder->keys || PyList_Append(decoder->keys, key)) {
                    Py_CLEAR(result);
                    break;
                }
            }
            PyObject *obj = decode_one(decoder);
            if (!obj) {
                Py_CLEAR(result);
                Py_XDECREF(key);
                break;
            }
            if (decoder->document_class ? PyObject_SetItem(result, key, obj) : PyDict_SetItem(result, key, obj)) {
                Py_XDECREF(key);
                Py_XDECREF(obj);
                Py_CLEAR(result);
                break;
            }
            Py_XDECREF(obj);
            Py_XDECREF(key);
        }
    }
    return result;
}

static PyObject *
decode_one(PyDecoder *decoder)
{
    PyObject *temp=NULL;
    if (decoder->len) {
        unsigned char first_byte = *decoder->data++;
        unsigned token = first_byte & 0xe0;
        if (!token) {
            switch (first_byte) {
                case Enc_FALSE:
                    Py_INCREF(Py_False);
                    return Py_False;
                    
                case Enc_TRUE:
                    Py_INCREF(Py_True);
                    return Py_True;
                    
                case Enc_NULL:
                    Py_INCREF(Py_None);
                    return Py_None;

                case Enc_INF:
                case Enc_NEGINF:
                case Enc_NAN:
                    return decode_special_float(decoder, first_byte);

                case Enc_TERMINATED_LIST:
                    return decode_list(decoder, -1);

                case Enc_CUSTOM:
                    temp = decode_one(decoder);
                    if (decoder->custom) {
                        PyObject *newobj = PyObject_CallFunctionObjArgs(decoder->custom, temp, NULL);
                        Py_CLEAR(temp);
                        if (newobj) {
                            temp = newobj;
                        }
                    }
                    return temp;

                default:
                    PyErr_SetString(PyExc_ValueError, "Invalid token in PBJSON string");
                    break;
            }
        }
        else {
            unsigned int len = first_byte & 0xf;
            if (first_byte & 0x10) {
                int lenlen = 0;
                if (len == 0xf) {
                    len = 0;
                    lenlen = 4;
                }
                else if (len >= 8) {
                    len &= 0x7;
                    lenlen = 2;
                }
                else {
                    len &= 7;
                    lenlen = 1;
                }
                if (decoder->len < lenlen) {
                    set_overflow();
                    return NULL;
                }
                while (lenlen) {
                    len <<= 8;
                    len |= *decoder->data++;
                    decoder->len--;
                    lenlen--;
                }
            }
            if (decoder->len < (int)len) {
                set_overflow();
                return NULL;
            }
            switch (token) {
                case Enc_INT:
                    return decode_int(decoder, len);

                case Enc_NEGINT:
                    return decode_negint(decoder, len);

                case Enc_FLOAT:
                    return decode_float(decoder, len);
                    
                case Enc_STRING:
                    return decode_string(decoder, len);
                    
                case Enc_BINARY:
                    return decode_binary(decoder, len);
                    
                case Enc_LIST:
                    return decode_list(decoder, len);
                    
                case Enc_DICT:
                    return decode_dict(decoder, len);
                    
            }
        }
    }
    return NULL;
}

PyDoc_STRVAR(pydoc_decode,
             "decode(bytes, document_class, float_class, custom, unicode_errors) -> object\n"
             "\n"
             "Decode the byte object into an object."
             );

static PyObject *
py_decode(PyObject* self UNUSED, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"data", "document_class", "float_class", "custom", "unicode_errors", NULL};

    PyDecoder decoder;
    Py_buffer buf;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "y*OOOz:decode", kwlist, &buf, &decoder.document_class, &decoder.float_class, &decoder.custom, &decoder.unicode_errors))
        return NULL;
    decoder.data = (unsigned char*)buf.buf;
    decoder.len = buf.len;
    if (decoder.document_class == Py_None || decoder.document_class == (PyObject *)&PyDict_Type) {
        decoder.document_class = NULL;
    }
    if (decoder.float_class == Py_None || decoder.float_class == (PyObject *)&PyFloat_Type) {
        decoder.float_class = NULL;
    }
    decoder.keys = NULL;
    PyObject *result = decode_one(&decoder);
    Py_CLEAR(decoder.keys);
    return result;
}






static int
flush_accumulator(PyEncoder *acc)
{
    if (acc->buffer) {
        if (acc->chunk_list == NULL) {
            acc->chunk_list = PyList_New(0);
            if (acc->chunk_list == NULL)
                return -1;
        }
        if (_PyString_Resize(&acc->buffer, acc->position)) {
            return -1;
        }
        if (PyList_Append(acc->chunk_list, acc->buffer)) {
            return -1;
        }
        Py_CLEAR(acc->buffer);
        acc->ptr = NULL;
        acc->position = 0;
    }
    return 0;
}

static int
JSON_Accu_Accumulate(PyEncoder *acc, const unsigned char *bytes, size_t len)
{
    if (!len) {
        return 0;
    }
    if (acc->position + len > BUFFER_SIZE) {
        if (flush_accumulator(acc)) {
            return -1;
        }
        if (len >= BUFFER_SIZE) {
            PyObject *s = PyString_FromStringAndSize((const char*)bytes, len);
            if (!s) {
                return -1;
            }
            if (PyList_Append(acc->chunk_list, s)) {
                return -1;
            }
            Py_DECREF(s);
            return 0;
        }
    }
    if (!acc->buffer) {
        acc->buffer = PyString_FromStringAndSize(NULL, BUFFER_SIZE);
        if (!acc->buffer) {
            return -1;
        }
        acc->ptr = (unsigned char*)PyString_AS_STRING(acc->buffer);
    }
    memcpy(acc->ptr, bytes, len);
    acc->ptr += len;
    acc->position += len;
    return 0;
}

static PyObject *
JSON_Accu_FinishAsList(PyEncoder *acc)
{
    int ret;
    PyObject *res=NULL;
    
    ret = flush_accumulator(acc);
    if (!ret) {
        res = acc->chunk_list;
        acc->chunk_list = NULL;
        if (res == NULL)
            res = PyList_New(0);
    }
    JSON_Accu_Destroy(acc);
    return res;
}

static void
JSON_Accu_Destroy(PyEncoder *acc)
{
    Py_CLEAR(acc->item_sort_kw);
    Py_CLEAR(acc->markers);
    Py_CLEAR(acc->key_memo);
    Py_CLEAR(acc->chunk_list);
    Py_CLEAR(acc->buffer);
}

static int
_is_namedtuple(PyObject *obj)
{
    int rval = 0;
    if (PyTuple_Check(obj)) {
        PyObject *_asdict = PyObject_GetAttrString(obj, "_asdict");
        if (_asdict == NULL) {
            PyErr_Clear();
            return 0;
        }
        rval = PyCallable_Check(_asdict);
        Py_DECREF(_asdict);
    }
    return rval;
}

static int
_has_for_json_hook(PyObject *obj)
{
    int rval = 0;
    PyObject *for_json = PyObject_GetAttrString(obj, "for_json");
    if (for_json == NULL) {
        PyErr_Clear();
        return 0;
    }
    rval = PyCallable_Check(for_json);
    Py_DECREF(for_json);
    return rval;
}


static int
encode_type_and_length(PyEncoder *rval, unsigned char token, int length)
{
    unsigned char buffer[5];
    if (length < 16) {
        token |= (unsigned char)length;
        return JSON_Accu_Accumulate(rval, &token, 1);
    }
    else if (length < 2048) {
        buffer[0] = token | 0x10 | (unsigned char)(length >> 8);
        buffer[1] = (unsigned char)length;
        return JSON_Accu_Accumulate(rval, buffer, 2);
    }
    else if (length < 458752) {
        buffer[0] = token | 0x18 | (unsigned char)(length >> 16);
        buffer[1] = (unsigned char)(length >> 8);
        buffer[2] = (unsigned char)length;
        return JSON_Accu_Accumulate(rval, buffer, 3);
    }
    buffer[0] = token | 0x1f;
    buffer[1] = (unsigned char)(length >> 24);
    buffer[2] = (unsigned char)(length >> 16);
    buffer[3] = (unsigned char)(length >> 8);
    buffer[4] = (unsigned char)length;
    return JSON_Accu_Accumulate(rval, buffer, 5);
}


static int
encode_type_and_content(PyEncoder *rval, unsigned char token, unsigned char *bytes, int length)
{
    if (encode_type_and_length(rval, token, length)) {
        return -1;
    }
    return JSON_Accu_Accumulate(rval, bytes, length);
}

static int
encode_long_no_overflow(PyEncoder *rval, long long value)
{
    unsigned char buffer[8];
    unsigned char token;
    if (value >= 0) {
        token = Enc_INT;
    } else {
        token = Enc_NEGINT;
        value = -value;
    }
    int i=0;
    buffer[0] = (unsigned char)(value >> 56);
    buffer[1] = (unsigned char)(value >> 48);
    buffer[2] = (unsigned char)(value >> 40);
    buffer[3] = (unsigned char)(value >> 32);
    buffer[4] = (unsigned char)(value >> 24);
    buffer[5] = (unsigned char)(value >> 16);
    buffer[6] = (unsigned char)(value >> 8);
    buffer[7] = (unsigned char)value;
    for (; i<8; i++) {
        if (buffer[i])
            break;
    }
    if (encode_type_and_length(rval, token, 8-i)) {
        PyErr_Clear();
        return -1;
    }
    return JSON_Accu_Accumulate(rval, buffer+i, 8-i);
}

static int
encode_long(PyEncoder *rval, PyObject *obj)
{
    int overflow;
    int count = 0;
    int err;
    PyObject *work=NULL;
    unsigned PY_LONG_LONG ull;
    long l = PyLong_AsLongAndOverflow(obj, &overflow);
    if (!overflow) {
        return encode_long_no_overflow(rval, l);
    }
    if (overflow >= 0) {
        Py_INCREF(obj);
    } else {
        obj = PyNumber_Negative(obj);
    }
    PyObject *list = PyList_New(0);
    PyObject *n64 = PyLong_FromLongLong(64);
    int ret=0;
    do {
        unsigned char buffer[8];
        ull = PyLong_AsUnsignedLongLong(obj);
        err = PyErr_Occurred() ? 1 : 0;
        if (err) {
            PyErr_Clear();
            ull = PyLong_AsUnsignedLongLongMask(obj);
            work = PyNumber_Rshift(obj, n64);
            Py_DECREF(obj);
            obj = work;
        }
        buffer[0] = (unsigned char)(ull >> 56);
        buffer[1] = (unsigned char)(ull >> 48);
        buffer[2] = (unsigned char)(ull >> 40);
        buffer[3] = (unsigned char)(ull >> 32);
        buffer[4] = (unsigned char)(ull >> 24);
        buffer[5] = (unsigned char)(ull >> 16);
        buffer[6] = (unsigned char)(ull >> 8);
        buffer[7] = (unsigned char)ull;
        int i=0;
        if (!err) {
            for (; i<8; i++) {
                if (buffer[i])
                    break;
            }
        }
        work = PyString_FromStringAndSize((const char*)buffer+i, 8-i);
        count += (8-i);
        if (work) {
            ret = PyList_Insert(list, 0, work);
            Py_CLEAR(work);
        } else {
            ret = -1;
        }
    } while (err && !ret);
    if (!ret) {
        work = join_list_bytes(list);
        ret = encode_type_and_content(rval, overflow>0 ? Enc_INT : Enc_NEGINT, (unsigned char*)PyString_AS_STRING(work), count);
        Py_CLEAR(work);
    }
    Py_DECREF(n64);
    Py_DECREF(obj);
    Py_CLEAR(list);
    return ret;
}

#define USE_FAST_DTOA

#define FLOAT_BUFFER 0x20
unsigned char dtoa(double value, char str[FLOAT_BUFFER])
{
    if (!value) {
        str[0]='0';
        str[1]=0;
        return Enc_FLOAT;
    }
    if (value - value != 0.0)
    {
        if (value != value)
            return Enc_NAN;
        else
            return value<0 ? Enc_NEGINF : Enc_INF;
    }

#ifdef USE_FAST_DTOA
    char buffer[FLOAT_BUFFER];
    /* if input is larger than thres_max, revert to exponential */
    const double thres_max = (double)(0x7FFFFFFF);
    int prec = 16;

    /* we'll work in positive values and deal with the
     negative sign issue later */
    int neg = 0;
    if (value < 0) {
        neg = 1;
        value = -value;
    }

    /* for very large numbers switch back to native sprintf for exponentials.
     anyone want to write code to replace this? */
    /*
     normal printf behavior is to print EVERY whole number digit
     which can be 100s of characters overflowing your buffers == bad
     */
    if (value > thres_max || value < .0001) {
        if (neg) {
            value = -value;
        }
#if PY_VERSION_HEX < 0x02070000
        PyOS_snprintf(str, FLOAT_BUFFER, "%e", value);
#else
        /* returns value using Python's 'repr' format */
        char *m = PyOS_double_to_string(value, 'r', 0, 0, 0);
        strcpy(str, m);
        PyMem_Free(m);
#endif
        return Enc_FLOAT;
    }
    
    int count;
    double diff = 0.0;
    char* wstr = buffer;
    
    uint64_t whole = value;
    uint64_t frac;
    if (whole) {
        frac = whole;
        while (frac>9) {
            frac /= 10;
            --prec;
        }
    }
    else if (value < .1) {
        ++prec;
        if (value < .01) {
            ++prec;
            if (value < .001) {
                ++prec;
            }
        }
    }
    double p = pow(10, prec);
    double tmp = (value - whole) * p;
    frac = (uint64_t)(tmp);
    diff = tmp - frac;
    uint64_t p_div_10 = p/10;

    /* add one digit of precision back if our frac is not maxed out */
    if (diff && frac < p_div_10) {
        frac *= 10;
        tmp = diff*10;
        frac += (int)tmp;
        diff = tmp - (int)tmp;
        p_div_10 = p;
        p *= 10;
        prec += 1;
    }
    
    if (diff > 0.5 && frac != p_div_10) {
        /* treat edge of precision as one precision lower */
        if (frac > p_div_10) {
            int mod = frac%10;
            if (mod > 5) {
                frac += (10-mod);
            } else if (mod && mod < 5) {
                frac -= mod;
            }
        } else {
            ++frac;
        }
        /* handle rollover, e.g.  case 0.99 with prec 1 is 1.0  */
        if (frac >= p) {
            frac = 0;
            ++whole;
        }
    } else if (diff == 0.5 && ((frac == 0) || (frac & 1))) {
        /* if halfway, round up if odd, OR
         if last digit is 0.  That last part is strange */
        ++frac;
    } else if (!diff && frac > p_div_10 && (frac % 100) == 1) {
        --frac;
    }
    
    if (prec == 0) {
        diff = value - whole;
        if (diff > 0.5) {
            /* greater than 0.5, round up, e.g. 1.6 -> 2 */
            ++whole;
        } else if (diff == 0.5 && (whole & 1)) {
            /* exactly 0.5 and ODD, then round up */
            /* 1.5 -> 2, but 2.5 -> 2 */
            ++whole;
        }
    } else if (frac) {
        count = prec;
        // now do fractional part, as an unsigned number
        // we know it is not 0 but we can have leading zeros, these
        // should be removed
        while (!(frac % 10)) {
            --count;
            frac /= 10;
        }
        
        // now do fractional part, as an unsigned number
        do {
            --count;
            *wstr++ = (char)(48 + (frac % 10));
        } while (frac /= 10);
        // add extra 0s
        while (count-- > 0) *wstr++ = '0';
        // add decimal
        *wstr++ = '.';
    }
    
    // do whole part
    // Take care of sign
    // Conversion. Number is reversed.
    do *wstr++ = (char)(48 + (whole % 10)); while (whole /= 10);
    if (neg) {
        *wstr++ = '-';
    }
    while (--wstr >= buffer) {
        *str++ = *wstr;
    }
    *str = 0;
#else
#if PY_VERSION_HEX < 0x02070000
    PyOS_snprintf(str, FLOAT_BUFFER, "%e", value);
#else
    char *m = PyOS_double_to_string(value, 'r', 0, 0, 0);
    strcpy(str, m);
    PyMem_Free(m);
#endif
#endif

    return Enc_FLOAT;
}

static int
encode_float_from_charstring(PyEncoder *rval, const char* str, int len, unsigned char token)
{
    int rv = -1;
    int i;
    if (token != Enc_FLOAT) {
        rv = JSON_Accu_Accumulate(rval, &token, 1);
    }
    else {
        unsigned char c;
        int nibble_index=0;
        if (str[0] == '-') {
            c = FltEnc_Minus << 4;
            nibble_index=1;
            ++str;
            --len;
        }
        while (len > 0 && *str == '0') {
            --len;
            ++str;
        }
        if (len > 1 && str[len-1] == '0' && str[len-2] == '.') {
            len -= 2;
        }

        rv = encode_type_and_length(rval, Enc_FLOAT, (len+1+nibble_index)/2);
        for (i=0; i<len && !rv; i++) {
            char nibble = str[i];
            if (nibble>='0' && nibble<='9') {
                nibble -= '0';
            }
            else if (nibble == '-') {
                nibble = FltEnc_Minus;
            }
            else if (nibble == '+') {
                nibble = FltEnc_Plus;
            }
            else if (nibble == '.') {
                nibble = FltEnc_Decimal;
            }
            else if (nibble == 'e') {
                nibble = FltEnc_E;
            }
            if (!nibble_index) {
                nibble_index = 1;
                c = nibble << 4;
            } else {
                c |= nibble;
                nibble_index = 0;
                rv = JSON_Accu_Accumulate(rval, &c, 1);
            }
        }
        if (!rv && nibble_index) {
            c |= FltEnc_Decimal;
            rv = JSON_Accu_Accumulate(rval, &c, 1);
        }
    }
    return rv;
}

static int
encode_float(PyEncoder *rval, PyObject *obj)
{
#if 1
    char buffer[FLOAT_BUFFER];
    double d = PyFloat_AS_DOUBLE(obj);
    unsigned char token = dtoa(d, buffer);
    return encode_float_from_charstring(rval, buffer, strlen(buffer), token);
#else
    PyObject *encoded = PyObject_Str(obj);
    if (!encoded) {
        return -1;
    }
#if PY_MAJOR_VERSION >= 3
    obj = encoded;
    encoded = PyUnicode_AsUTF8String(obj);
    if (!encoded) {
        Py_XDECREF(obj);
        return -1;
    }
#endif
    const char* str = PyString_AS_STRING(encoded);
    int len = PyString_GET_SIZE(encoded);
    unsigned char token = Enc_FLOAT;
    if (len) {
        if (str[0] == 'i') {
            token = Enc_INF;
        }
        else if (str[0] == 'n') {
            token = Enc_NAN;
        }
        else if (str[0] == '-' && str[1] == 'i') {
            token = Enc_NEGINF;
        }
    }
    int rv = encode_float_from_charstring(rval, str, len, token);
    Py_XDECREF(encoded);
    return rv;
#endif
}

static int
encode_decimal(PyEncoder *rval, PyObject *obj)
{
    PyObject *encoded = PyObject_Str(obj);
    if (!encoded) {
        return -1;
    }
#if PY_MAJOR_VERSION >= 3
    obj = encoded;
    encoded = PyUnicode_AsUTF8String(obj);
    if (!encoded) {
        Py_XDECREF(obj);
        return -1;
    }
#endif
    const char* str = PyString_AS_STRING(encoded);
    int len = PyString_GET_SIZE(encoded);
    unsigned char token = Enc_FLOAT;
    if (len) {
        if (str[0] == 'I') {
            token = Enc_INF;
        }
        else if (str[0] == 'N') {
            token = Enc_NAN;
        }
        else if (str[0] == '-' && str[1] == 'I') {
            token = Enc_NEGINF;
        }
    }
    int rv = encode_float_from_charstring(rval, str, len, token);
    Py_XDECREF(encoded);
    return rv;
}


static int
encode_key(PyEncoder *rval, PyObject *obj)
{
    PyObject *encoded = NULL;
    PyObject *value = NULL;
    const char* str = NULL;
    Py_ssize_t len = 0;
    if (PyUnicode_Check(obj))
    {
        encoded = PyUnicode_AsUTF8String(obj);
        if (!encoded) {
            return -1;
        }
    }
#if PY_MAJOR_VERSION < 3
    else if (PyString_Check(obj))
    {
        Py_INCREF(obj);
        encoded = obj;
    }
#endif
    else {
        return -1;
    }
    if (!str) {
        str = PyString_AS_STRING(encoded);
        len = PyString_GET_SIZE(encoded);
    }
    unsigned char clen = (unsigned char)len;
    if (len > 127 || JSON_Accu_Accumulate(rval, &clen, 1)) {
        Py_DECREF(encoded);
        return -1;
    }
    int ret = JSON_Accu_Accumulate(rval, (unsigned char*)str, len);
    if (rval->key_memo) {
        len = PyDict_Size(rval->key_memo);
    }
    else {
        rval->key_memo = PyDict_New();
        len = 0;
    }
    if (len < 128) {
        PyObject *value = PyLong_FromLong(len);
        if (PyDict_SetItem(rval->key_memo, obj, value))
            ret = -1;
    }
    Py_CLEAR(value);
    Py_DECREF(encoded);
    return ret;
}

static int
check_circular(PyEncoder *rval, PyObject *obj, PyObject **ident_ptr)
{
    int has_key;
    PyObject *ident = NULL;
    if (!rval->markers) {
        rval->markers = PyDict_New();
        if (!rval->markers) {
            return -1;
        }
    }
    ident = PyLong_FromVoidPtr(obj);
    if (ident == NULL)
        return -1;
    has_key = PyDict_Contains(rval->markers, ident);
    if (has_key) {
        if (has_key != -1)
            PyErr_SetString(PyExc_ValueError, "Circular reference detected");
        Py_DECREF(ident);
        return -1;
    }
    if (PyDict_SetItem(rval->markers, ident, obj)) {
        Py_DECREF(ident);
        return -1;
    }
    *ident_ptr = ident;
    return 0;
}

static int
encode_one(PyEncoder *encoder, PyObject *obj)
{
    /* Encode Python object obj to a byte object */
    int rv = -1;
    do {
        if (obj == Py_None || obj == Py_True || obj == Py_False) {
            unsigned char c = obj == Py_False ? Enc_FALSE : obj == Py_True ? Enc_TRUE : Enc_NULL;
            rv = JSON_Accu_Accumulate(encoder, &c, 1);
        }
        else if (PyUnicode_Check(obj))
        {
            PyObject *encoded = PyUnicode_AsUTF8String(obj);
            if (encoded != NULL) {
                rv = encode_type_and_content(encoder, Enc_STRING, (unsigned char*)PyString_AS_STRING(encoded), PyString_GET_SIZE(encoded));
                Py_DECREF(encoded);
            }
        }
#if PY_MAJOR_VERSION >= 3
        else if (PyBytes_Check(obj))
        {
            rv = encode_type_and_content(encoder, Enc_BINARY, (unsigned char*)PyBytes_AS_STRING(obj), PyBytes_GET_SIZE(obj));
        }
#else
        else if (PyString_Check(obj))
        {
            rv = encode_type_and_content(encoder, Enc_STRING, (unsigned char*)PyString_AS_STRING(obj), PyString_GET_SIZE(obj));
        }
        else if (PyInt_Check(obj)) {
            rv = encode_long_no_overflow(encoder, PyInt_AS_LONG(obj));
        }
#endif
        else if (PyLong_Check(obj)) {
            rv = encode_long(encoder, obj);
        }
        else if (PyFloat_Check(obj)) {
            rv = encode_float(encoder, obj);
        }
        else if (encoder->Decimal && PyObject_TypeCheck(obj, (PyTypeObject *)encoder->Decimal)) {
            rv = encode_decimal(encoder, obj);
        }
        else {
            if (encoder->custom) {
                PyObject *callable=NULL;
                if (encoder->single_custom) {
                    if (PyObject_IsInstance(obj, PyTuple_GET_ITEM(encoder->custom, 0))) {
                        callable = PyTuple_GET_ITEM(encoder->custom, 1);
                    }
                } else {
                    PyObject *tuple;
                    PyObject *iter = PyObject_GetIter(encoder->custom);
                    if (iter == NULL)
                        return -1;
                    while ((tuple = PyIter_Next(iter)) && !callable && !PyErr_Occurred()) {
                        if (!PyTuple_Check(tuple) || Py_SIZE(tuple) != 2) {
                            PyErr_SetString(PyExc_ValueError, "Custom handlers must be a sequence of 2-tuples (type, function)");
                        }
                        else if (PyObject_IsInstance(obj, PyTuple_GET_ITEM(tuple, 0))) {
                            callable = PyTuple_GET_ITEM(tuple, 1);
                        }
                        Py_CLEAR(tuple);
                    }
                    Py_CLEAR(iter);
                }
                if (callable) {
                    PyObject *ident = NULL;
                    PyObject *newobj;
                    if (encoder->check_circular && check_circular(encoder, obj, &ident)) {
                        break;
                    }
                    PyErr_Clear();
                    newobj = PyObject_CallFunctionObjArgs(callable, obj, NULL);
                    if (newobj) {
                        unsigned char c = Enc_CUSTOM;
                        rv = JSON_Accu_Accumulate(encoder, &c, 1);
                        rv = encode_one(encoder, newobj);
                        Py_XDECREF(newobj);
                    }
                    if (rv) {
                        rv = -1;
                    }
                    else if (ident != NULL) {
                        if (PyDict_DelItem(encoder->markers, ident)) {
                            rv = -1;
                        }
                    }
                    Py_XDECREF(ident);
                    break;
                }
                if (PyErr_Occurred()) {
                    rv = -1;
                    break;
                }
            }
            if (encoder->for_json && _has_for_json_hook(obj)) {
                PyObject *newobj;
                if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                    return rv;
                newobj = PyObject_CallMethod(obj, "for_json", NULL);
                if (newobj != NULL) {
                    rv = encode_one(encoder, newobj);
                    Py_DECREF(newobj);
                }
                Py_LeaveRecursiveCall();
            }
            else if (PyObject_IsInstance(obj, encoder->Mapping)) {
                if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                    return rv;
                rv = encode_dict(encoder, obj);
                Py_LeaveRecursiveCall();
            }
            else if (_is_namedtuple(obj)) {
                PyObject *newobj;
                if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                    return rv;
                newobj = PyObject_CallMethod(obj, "_asdict", NULL);
                if (newobj != NULL) {
                    rv = encode_dict(encoder, newobj);
                    Py_DECREF(newobj);
                }
                Py_LeaveRecursiveCall();
            }
            else if (PyObject_Length(obj) >= 0) {
                if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                    return rv;
                rv = encode_list(encoder, obj);
                Py_LeaveRecursiveCall();
            }
            else {
                PyErr_Clear();
                if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                    return rv;
                PyObject *iter = PyObject_GetIter(obj);
                if (iter) {
                    rv = encode_terminated_list(encoder, iter);
                    Py_XDECREF(iter);
                } else {
                    PyObject *ident = NULL;
                    PyObject *newobj;
                    if (encoder->check_circular && check_circular(encoder, obj, &ident)) {
                        break;
                    }
                    PyErr_Clear();
                    newobj = PyObject_CallFunctionObjArgs(encoder->defaultfn, obj, NULL);
                    if (newobj) {
                        rv = encode_one(encoder, newobj);
                        Py_XDECREF(newobj);
                    }
                    if (rv) {
                        rv = -1;
                    }
                    else if (ident != NULL) {
                        if (PyDict_DelItem(encoder->markers, ident)) {
                            rv = -1;
                        }
                    }
                    Py_XDECREF(ident);
                }
                Py_LeaveRecursiveCall();
            }
        }
    } while (0);
    return rv;
}

static int
encode_dict(PyEncoder *encoder, PyObject *dct)
{
    /* Encode Python dict dct a JSON term */
    PyObject *kstr = NULL;
    PyObject *ident = NULL;
    PyObject *iter = NULL;
    PyObject *item = NULL;
    PyObject *items = NULL;
    PyObject *encoded = NULL;
    Py_ssize_t idx;

    int len = PyMapping_Size(dct);
    if (encode_type_and_length(encoder, Enc_DICT, len)) {
        return -1;
    }

    if (len) {
        if (encoder->check_circular && check_circular(encoder, dct, &ident)) {
            goto bail;
        }
        
        iter = encode_dict_items(encoder, dct);
        if (iter == NULL)
            goto bail;
        
        idx = 0;
        while ((item = PyIter_Next(iter))) {
            PyObject *encoded, *key, *value;
            if (!PyTuple_Check(item) || Py_SIZE(item) != 2) {
                PyErr_SetString(PyExc_ValueError, "items must return 2-tuples");
                goto bail;
            }
            key = PyTuple_GET_ITEM(item, 0);
            if (key == NULL)
                goto bail;
            value = PyTuple_GET_ITEM(item, 1);
            if (value == NULL)
                goto bail;

            encoded = encoder->key_memo ? PyDict_GetItem(encoder->key_memo, key) : NULL;
            if (encoded != NULL) {
                long value = PyLong_AS_LONG(encoded);
                unsigned char l = 0x80 | (unsigned char)value;
                if (JSON_Accu_Accumulate(encoder, &l, 1)) {
                    goto bail;
                }
            } else if (encode_key(encoder, key)) {
                goto bail;
            }
            if (encode_one(encoder, value))
                goto bail;
            Py_CLEAR(item);
            idx += 1;
        }
        Py_CLEAR(iter);
        if (PyErr_Occurred())
            goto bail;
        if (ident != NULL) {
            if (PyDict_DelItem(encoder->markers, ident))
                goto bail;
            Py_CLEAR(ident);
        }
    }
    return 0;

bail:
    Py_XDECREF(encoded);
    Py_XDECREF(items);
    Py_XDECREF(iter);
    Py_XDECREF(kstr);
    Py_XDECREF(ident);
    return -1;
}


static int
encode_list(PyEncoder *encoder, PyObject *seq)
{
    /* Encode Python list seq to a JSON term */
    PyObject *iter = NULL;
    PyObject *obj = NULL;
    PyObject *ident = NULL;
    int len = PyObject_Length(seq);
    if (encode_type_and_length(encoder, Enc_LIST, len)) {
        return -1;
    }

    if (len) {
        if (encoder->check_circular && check_circular(encoder, seq, &ident)) {
            goto bail;
        }
        
        iter = PyObject_GetIter(seq);
        if (iter == NULL)
            goto bail;
        
        while ((obj = PyIter_Next(iter))) {
            if (encode_one(encoder, obj))
                goto bail;
            Py_CLEAR(obj);
        }
        Py_CLEAR(iter);
        if (PyErr_Occurred())
            goto bail;
        if (ident != NULL) {
            if (PyDict_DelItem(encoder->markers, ident))
                goto bail;
            Py_CLEAR(ident);
        }
    }
    return 0;

bail:
    Py_XDECREF(obj);
    Py_XDECREF(iter);
    Py_XDECREF(ident);
    return -1;
}

static int
encode_terminated_list(PyEncoder *encoder, PyObject *iter)
{
    /* Encode Python list seq to a JSON term */
    PyObject *obj = NULL;
    
    unsigned char c = Enc_TERMINATED_LIST;
    if (JSON_Accu_Accumulate(encoder, &c, 1))
        return -1;

    while ((obj = PyIter_Next(iter))) {
        int rv = encode_one(encoder, obj);
        Py_XDECREF(obj);
        if (rv) {
            return -1;
        }
    }
    if (PyErr_Occurred())
        return -1;
    c = Enc_TERMINATOR;
    if (JSON_Accu_Accumulate(encoder, &c, 1))
        return -1;
    return 0;
}

static PyObject *
encode_dict_items(PyEncoder *encoder, PyObject *dct)
{
    PyObject *items;
    PyObject *iter = NULL;
    PyObject *lst = NULL;
    PyObject *item = NULL;
    PyObject *kstr = NULL;
    static PyObject *sortfun = NULL;
    static PyObject *sortargs = NULL;
    
    if (sortargs == NULL) {
        sortargs = PyTuple_New(0);
        if (sortargs == NULL)
            return NULL;
    }
    
    if (PyDict_CheckExact(dct))
        items = PyDict_Items(dct);
    else
        items = PyMapping_Items(dct);
    if (items == NULL)
        return NULL;
    iter = PyObject_GetIter(items);
    Py_DECREF(items);
    if (iter == NULL)
        return NULL;
    if (encoder->item_sort_kw == NULL)
        return iter;
    lst = PyList_New(0);
    if (lst == NULL)
        goto bail;
    while ((item = PyIter_Next(iter))) {
        PyObject *key;
        if (!PyTuple_Check(item) || Py_SIZE(item) != 2) {
            PyErr_SetString(PyExc_ValueError, "items must return 2-tuples");
            goto bail;
        }
        key = PyTuple_GET_ITEM(item, 0);
        if (key == NULL)
            goto bail;
#if PY_MAJOR_VERSION < 3
        else if (PyString_Check(key)) {
            /* item can be added as-is */
        }
#endif /* PY_MAJOR_VERSION < 3 */
        else if (PyUnicode_Check(key)) {
            /* item can be added as-is */
        }
        else {
            goto bail;
        }
        if (PyList_Append(lst, item))
            goto bail;
        Py_DECREF(item);
    }
    Py_CLEAR(iter);
    if (PyErr_Occurred())
        goto bail;
    sortfun = PyObject_GetAttrString(lst, "sort");
    if (sortfun == NULL)
        goto bail;
    if (!PyObject_Call(sortfun, sortargs, encoder->item_sort_kw))
        goto bail;
    Py_CLEAR(sortfun);
    iter = PyObject_GetIter(lst);
    Py_CLEAR(lst);
    return iter;
bail:
    Py_XDECREF(sortfun);
    Py_XDECREF(kstr);
    Py_XDECREF(item);
    Py_XDECREF(lst);
    Py_XDECREF(iter);
    return NULL;
}


PyDoc_STRVAR(pydoc_encode,
             "encode(object, Decimal, Mapping, skip_illegal_keys, check_circular, sort_keys, convert, use_for_json) -> object\n"
             "\n"
             "Encode the object into a byte object."
             );


static int
convert_to_bool(PyObject *o, int *value)
{
    *value = (o && PyObject_IsTrue(o)) ? 1 : 0;
    return 1;
}

static PyObject *
py_encode(PyObject* self UNUSED, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"object", "Decimal", "Mapping", "skip_illegal_keys", "check_circular", "sort_keys", "custom", "convert", "use_for_json", NULL};

    PyObject *obj=NULL;
    PyObject *sort_keys=NULL;
    PyEncoder encoder;
    memset(&encoder, 0, sizeof(encoder));
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|OOO&O&OOOO&:encode", kwlist, &obj, &encoder.Decimal, &encoder.Mapping, convert_to_bool, &encoder.skipkeys, convert_to_bool, &encoder.check_circular, &sort_keys, &encoder.custom, &encoder.defaultfn, convert_to_bool, &encoder.for_json))
        return NULL;
    if (encoder.Decimal == Py_None || encoder.Decimal == (PyObject *)&PyFloat_Type) {
        encoder.Decimal = NULL;
    }
    if (encoder.custom == Py_None || (encoder.custom && PyObject_Length(encoder.custom) == 0)) {
        encoder.custom = NULL;
    } else {
        encoder.single_custom = PyTuple_Check(encoder.custom) && Py_SIZE(encoder.custom) == 2 && PyType_Check(PyTuple_GET_ITEM(encoder.custom, 0));
    }
    if (sort_keys != Py_None) {
        encoder.item_sort_kw = PyDict_New();
        if (encoder.item_sort_kw == NULL)
            return NULL;
        if (PyDict_SetItemString(encoder.item_sort_kw, "key", sort_keys)) {
            Py_CLEAR(encoder.item_sort_kw);
            return NULL;
        }
    }
    if (encode_one(&encoder, obj)) {
        JSON_Accu_Destroy(&encoder);
        return NULL;
    }
    return JSON_Accu_FinishAsList(&encoder);
}


static PyMethodDef speedups_methods[] = {
    {"decode",
        (PyCFunction)py_decode,
        METH_VARARGS | METH_KEYWORDS,
        pydoc_decode},
    {"encode",
        (PyCFunction)py_encode,
        METH_VARARGS | METH_KEYWORDS,
        pydoc_encode},
    {NULL, NULL, 0, NULL}
};

PyDoc_STRVAR(module_doc,
"pbjson speedups\n");

#if PY_MAJOR_VERSION >= 3
static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_speedups", /* m_name */
    module_doc,         /* m_doc */
    -1,                 /* m_size */
    speedups_methods,   /* m_methods */
    NULL,               /* m_reload */
    NULL,               /* m_traverse */
    NULL,               /* m_clear*/
    NULL,               /* m_free */
};
#endif

static PyObject *
moduleinit(void)
{
    PyObject *m;

#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule3("_speedups", speedups_methods, module_doc);
#endif
    return m;
}

#if PY_MAJOR_VERSION >= 3
PyMODINIT_FUNC
PyInit__speedups(void)
{
    return moduleinit();
}
#else
void
init_speedups(void)
{
    moduleinit();
}
#endif
