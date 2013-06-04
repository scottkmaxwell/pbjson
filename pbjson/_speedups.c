/* -*- mode: C; c-file-style: "python"; c-basic-offset: 4 -*- */
#include "Python.h"
#include "structmember.h"

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromSsize_t PyLong_FromSsize_t
#define PyInt_AsSsize_t PyLong_AsSsize_t
#define PyString_Check PyBytes_Check
#define PyString_GET_SIZE PyBytes_GET_SIZE
#define PyString_AS_STRING PyBytes_AS_STRING
#define PyString_FromStringAndSize PyBytes_FromStringAndSize
#define _PyString_Resize _PyBytes_Resize
#define PyInt_Check(obj) 0
#define JSON_UNICHR Py_UCS4
#define JSON_InternFromString PyBytes_FromString
#define JSON_InternFromStringAndSize PyBytes_FromStringAndSize
#define JSON_Intern_GET_SIZE PyUnicode_GET_SIZE
#define JSON_ASCII_Check PyUnicode_Check
#define JSON_ASCII_AS_STRING PyUnicode_AsUTF8
#define PyInt_Type PyLong_Type
#define PyInt_FromString PyLong_FromString
#define PY2_UNUSED
#define PY3_UNUSED UNUSED
#define JSON_NewEmptyUnicode() PyUnicode_New(0, 127)
#define JSON_NewEmptyBytes() PyBytes_FromStringAndSize(NULL, 0)
#else /* PY_MAJOR_VERSION >= 3 */
#define PY2_UNUSED UNUSED
#define PY3_UNUSED
#define PyUnicode_READY(obj) 0
#define PyUnicode_KIND(obj) (sizeof(Py_UNICODE))
#define PyUnicode_DATA(obj) ((void *)(PyUnicode_AS_UNICODE(obj)))
#define PyUnicode_READ(kind, data, index) ((JSON_UNICHR)((const Py_UNICODE *)(data))[(index)])
#define PyUnicode_GetLength PyUnicode_GET_SIZE
#define JSON_UNICHR Py_UNICODE
#define JSON_ASCII_Check PyString_Check
#define JSON_ASCII_AS_STRING PyString_AS_STRING
#define JSON_InternFromString PyString_InternFromString
#define JSON_Intern_GET_SIZE PyString_GET_SIZE
#define JSON_NewEmptyUnicode() PyUnicode_FromUnicode(NULL, 0)
#endif /* PY_MAJOR_VERSION < 3 */

#define Enc_FALSE 0
#define Enc_TRUE 1
#define Enc_NULL 2
#define Enc_INF 3
#define Enc_NEGINF 4
#define Enc_NAN 5
#define Enc_TERMINATED_LIST 0xc
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
#define PyInt_FromSsize_t PyInt_FromLong
#define PyInt_AsSsize_t PyInt_AsLong
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

#define DEFAULT_ENCODING "utf-8"

#define PyDecoder_Check(op) PyObject_TypeCheck(op, &PyDecoderType)
#define PyDecoder_CheckExact(op) (Py_TYPE(op) == &PyDecoderType)
#define PyEncoder_Check(op) PyObject_TypeCheck(op, &PyEncoderType)
#define PyEncoder_CheckExact(op) (Py_TYPE(op) == &PyEncoderType)

#define JSON_ALLOW_NAN 1
#define JSON_IGNORE_NAN 2

static PyTypeObject PyEncoderType;

typedef struct {
    PyObject *markers;      /* Dict for tracking circular references */
    PyObject *key_memo;     /* Place to keep track of previously used keys */
    PyObject *chunk_list;   /* A list of previously accumulated strings */
    PyObject *buffer;       /* A string for building up a chunk */
    unsigned char* ptr;     /* Pointer into the buffer */
    int position;           /* How far into the buffer we have written */
} JSON_Accu;

typedef struct _PyDecoder {
    PyObject *document_class;
    PyObject *float_class;
    PyObject *keys;
    const char* data;
    int len;
} PyDecoder;


static int
JSON_Accu_Init(JSON_Accu *acc);
static int
JSON_Accu_Accumulate(JSON_Accu *acc, const unsigned char *bytes, size_t len);
static PyObject *
JSON_Accu_FinishAsList(JSON_Accu *acc);
static void
JSON_Accu_Destroy(JSON_Accu *acc);

#define ERR_EXPECTING_VALUE "Expecting value"
#define ERR_ARRAY_DELIMITER "Expecting ',' delimiter or ']'"
#define ERR_ARRAY_VALUE_FIRST "Expecting value or ']'"
#define ERR_OBJECT_DELIMITER "Expecting ',' delimiter or '}'"
#define ERR_OBJECT_PROPERTY "Expecting property name enclosed in double quotes"
#define ERR_OBJECT_PROPERTY_FIRST "Expecting property name enclosed in double quotes or '}'"
#define ERR_OBJECT_PROPERTY_DELIMITER "Expecting ':' delimiter"
#define ERR_STRING_UNTERMINATED "Unterminated string starting at"
#define ERR_STRING_CONTROL "Invalid control character %r at"
#define ERR_STRING_ESC1 "Invalid \\X escape sequence %r"
#define ERR_STRING_ESC4 "Invalid \\uXXXX escape sequence"

typedef struct _PyEncoderObject {
    PyObject_HEAD
    PyObject *defaultfn;
    PyObject *sort_keys;
    PyObject *Decimal;
    PyObject *skipkeys_bool;
    int check_circular;
    int skipkeys;
    PyObject *item_sort_kw;
    int for_json;
} PyEncoderObject;

static PyMemberDef encoder_members[] = {
    {"default", T_OBJECT, offsetof(PyEncoderObject, defaultfn), READONLY, "default"},
    {"sort_keys", T_OBJECT, offsetof(PyEncoderObject, sort_keys), READONLY, "sort_keys"},
    /* Python 2.5 does not support T_BOOl */
    {"skipkeys", T_OBJECT, offsetof(PyEncoderObject, skipkeys_bool), READONLY, "skipkeys"},
    {NULL}
};

static PyObject *
decode_one(PyDecoder *decoder);
#if PY_MAJOR_VERSION < 3
static PyObject *
join_list_string(PyObject *lst);
#else
static PyObject *
join_list_bytes(PyObject *lst);
#endif
static PyObject *
encoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static int
encoder_init(PyObject *self, PyObject *args, PyObject *kwds);
static void
encoder_dealloc(PyObject *self);
static int
encoder_clear(PyObject *self);
static int
encoder_listencode_list(PyEncoderObject *s, JSON_Accu *rval, PyObject *seq);
static int
encoder_listencode_sequence(PyEncoderObject *s, JSON_Accu *rval, PyObject *iter);
static int
encoder_listencode_obj(PyEncoderObject *s, JSON_Accu *rval, PyObject *obj);
static int
encoder_listencode_dict(PyEncoderObject *s, JSON_Accu *rval, PyObject *dct);
static void
raise_errmsg(char *msg, PyObject *s, Py_ssize_t end);
static PyObject *
_convertPyInt_FromSsize_t(Py_ssize_t *size_ptr);
static int
_is_namedtuple(PyObject *obj);
static int
_has_for_json_hook(PyObject *obj);
static PyObject *
moduleinit(void);

#define S_CHAR(c) (c >= ' ' && c <= '~' && c != '\\' && c != '"')
#define IS_WHITESPACE(c) (((c) == ' ') || ((c) == '\t') || ((c) == '\n') || ((c) == '\r'))

#define MIN_EXPANSION 6

static int
JSON_Accu_Init(JSON_Accu *acc)
{
    /* Lazily allocated */
    acc->markers = NULL;
    acc->key_memo = NULL;
    acc->chunk_list = NULL;
    acc->buffer = NULL;
    acc->ptr = NULL;
    acc->position = 0;
    return 0;
}

static int
flush_accumulator(JSON_Accu *acc)
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
JSON_Accu_Accumulate(JSON_Accu *acc, const unsigned char *bytes, size_t len)
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
JSON_Accu_FinishAsList(JSON_Accu *acc)
{
    int ret;
    PyObject *res;

    ret = flush_accumulator(acc);
    if (ret) {
        Py_CLEAR(acc->chunk_list);
        return NULL;
    }
    res = acc->chunk_list;
    acc->chunk_list = NULL;
    if (res == NULL)
        return PyList_New(0);
    return res;
}

static void
JSON_Accu_Destroy(JSON_Accu *acc)
{
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

static PyObject *
_convertPyInt_FromSsize_t(Py_ssize_t *size_ptr)
{
    /* Py_ssize_t to PyObject converter */
    return PyInt_FromSsize_t(*size_ptr);
}

static PyObject *
encoder_dict_iteritems(PyEncoderObject *s, PyObject *dct)
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
    if (s->item_sort_kw == Py_None)
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
    if (!PyObject_Call(sortfun, sortargs, s->item_sort_kw))
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

static void
raise_errmsg(char *msg, PyObject *s, Py_ssize_t end)
{
    /* Use JSONDecodeError exception to raise a nice looking ValueError subclass */
    static PyObject *JSONDecodeError = NULL;
    PyObject *exc;
    if (JSONDecodeError == NULL) {
        PyObject *scanner = PyImport_ImportModule("pbjson.scanner");
        if (scanner == NULL)
            return;
        JSONDecodeError = PyObject_GetAttrString(scanner, "JSONDecodeError");
        Py_DECREF(scanner);
        if (JSONDecodeError == NULL)
            return;
    }
    exc = PyObject_CallFunction(JSONDecodeError, "(zOO&)", msg, s, _convertPyInt_FromSsize_t, &end);
    if (exc) {
        PyErr_SetObject(JSONDecodeError, exc);
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
        PyObject *ustr = JSON_NewEmptyBytes();
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

PyDoc_STRVAR(pydoc_decode,
    "decode(basestring, document_class, float_class) -> object\n"
    "\n"
    "Decode the byte object into an object."
);

static void
set_overflow()
{
    
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
        result = PyNumber_InPlaceLshift(result, shifter);
        more = decode_unsigned_long_long(decoder, one_bite);
        result = PyNumber_InPlaceOr(result, more);
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
    PyObject *result = PyUnicode_FromStringAndSize(decoder->data, length);
    decoder->data += length;
    decoder->len -= length;
    return result;
}

static PyObject *
decode_binary(PyDecoder *decoder, int length)
{
    PyObject *result = PyBytes_FromStringAndSize(decoder->data, length);
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
                key = PyUnicode_FromStringAndSize(decoder->data, token);
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
                    
                default:
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
            if (decoder->len < len) {
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

static PyObject *
py_decode(PyObject* self UNUSED, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"data", "document_class", "float_class", NULL};

    PyDecoder decoder;
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "y#OO:decode", kwlist, &decoder.data, &decoder.len, &decoder.document_class, &decoder.float_class))
        return NULL;
    if (decoder.document_class == Py_None || decoder.document_class == (PyObject *)&PyDict_Type) {
        decoder.document_class = NULL;
    }
    if (decoder.float_class == Py_None || decoder.float_class == (PyObject *)&PyFloat_Type) {
        decoder.float_class = NULL;
    }
    decoder.keys = NULL; //PyList_New(0);
    PyObject *result = decode_one(&decoder);
    Py_CLEAR(decoder.keys);
    return result;
}

//PyDoc_STRVAR(pydoc_make_encoder,
//    "make_encoder(basestring) -> str\n"
//    "\n"
//    "Return an ASCII-only JSON representation of a Python string"
//);



static PyObject *
encoder_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    PyEncoderObject *s;
    s = (PyEncoderObject *)type->tp_alloc(type, 0);
    if (s != NULL) {
        s->defaultfn = NULL;
        s->sort_keys = NULL;
        s->item_sort_kw = NULL;
        s->Decimal = NULL;
    }
    return (PyObject *)s;
}

static int
encoder_init(PyObject *self, PyObject *args, PyObject *kwds)
{
    /* initialize Encoder object */
    static char *kwlist[] = {"check_circular", "default", "sort_keys", "skipkeys", "for_json", "Decimal", NULL};

    PyEncoderObject *s;
    PyObject *check_circular, *defaultfn;
    PyObject *sort_keys, *skipkeys, *for_json;
    PyObject *Decimal;

    assert(PyEncoder_Check(self));
    s = (PyEncoderObject *)self;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OOOOOO:make_encoder", kwlist,
        &check_circular, &defaultfn,
        &sort_keys, &skipkeys,
        &for_json, &Decimal))
        return -1;

    s->check_circular = PyObject_IsTrue(check_circular);
    s->defaultfn = defaultfn;
    s->skipkeys_bool = skipkeys;
    s->skipkeys = PyObject_IsTrue(skipkeys);
    if (sort_keys == Py_None) {
        Py_INCREF(Py_None);
        s->item_sort_kw = Py_None;
    }
    else {
        s->item_sort_kw = PyDict_New();
        if (s->item_sort_kw == NULL)
            return -1;
        if (PyDict_SetItemString(s->item_sort_kw, "key", sort_keys))
            return -1;
    }
    s->sort_keys = sort_keys;
    s->Decimal = Decimal;
    s->for_json = PyObject_IsTrue(for_json);

    Py_INCREF(s->defaultfn);
    Py_INCREF(s->skipkeys_bool);
    Py_INCREF(s->sort_keys);
    Py_INCREF(s->Decimal);
    return 0;
}

static PyObject *
encoder_call(PyObject *self, PyObject *args, PyObject *kwds)
{
    /* Python callable interface to encode_listencode_obj */
    PyObject *obj;
    PyEncoderObject *s;
    JSON_Accu rval;
    assert(PyEncoder_Check(self));
    s = (PyEncoderObject *)self;
    if (!PyArg_ParseTuple(args, "O:_iterencode", &obj))
        return NULL;
    if (JSON_Accu_Init(&rval))
        return NULL;
    if (encoder_listencode_obj(s, &rval, obj)) {
        JSON_Accu_Destroy(&rval);
        return NULL;
    }
    return JSON_Accu_FinishAsList(&rval);
}

static int
encode_type_and_length(JSON_Accu *rval, unsigned char token, int length)
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
encode_type_and_content(JSON_Accu *rval, unsigned char token, unsigned char *bytes, int length)
{
    if (encode_type_and_length(rval, token, length)) {
        return -1;
    }
    return JSON_Accu_Accumulate(rval, bytes, length);
}

static int
encode_long_no_overflow(JSON_Accu *rval, long value)
{
    unsigned char buffer[8];
    unsigned char token;
    if (value >= 0) {
        token = Enc_INT;
    } else {
        token = Enc_NEGINT;
        value = -value;
    }
#if LONG_MAX > 0x100000000
    int i=0;
    buffer[0] = (unsigned char)(value >> 56);
    buffer[1] = (unsigned char)(value >> 48);
    buffer[2] = (unsigned char)(value >> 40);
    buffer[3] = (unsigned char)(value >> 32);
#else
    int i=4;
#endif
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
encode_long(JSON_Accu *rval, PyObject *obj)
{
    int overflow;
    int count = 0;
    int err;
    PyObject *work;
    unsigned PY_LONG_LONG ull;
    long l = PyLong_AsLongAndOverflow(obj, &overflow);
    if (!overflow) {
        return encode_long_no_overflow(rval, l);
    }
    if (overflow < 0) {
        work = PyNumber_Negative(obj);
        Py_DECREF(obj);
        obj = work;
    }
    PyObject *list = PyList_New(0);
    PyObject *n64 = PyLong_FromLong(64);
    do {
        unsigned char buffer[8];
        ull = PyLong_AsUnsignedLongLong(obj);
        err = PyErr_Occurred() ? 1 : 0;
        if (err) {
            PyErr_Clear();
            ull = PyLong_AsUnsignedLongLongMask(obj);
            obj = PyNumber_InPlaceRshift(obj, n64);
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
            for (i=0; i<8; i++) {
                if (buffer[i])
                    break;
            }
        }
        work = PyString_FromStringAndSize((const char*)buffer+i, 8-i);
        count += (8-i);
        if (!work) {
            Py_CLEAR(list);
            Py_CLEAR(n64);
            return -1;
        }
        if (PyList_Insert(list, 0, work)) {
            Py_CLEAR(work);
            Py_CLEAR(list);
            Py_CLEAR(n64);
            return -1;
        }
        Py_DECREF(work);
    } while (err);
    work = join_list_bytes(list);
    Py_CLEAR(list);
    Py_CLEAR(n64);
    if (!work) {
        return -1;
    }
    if (encode_type_and_length(rval, overflow>0 ? Enc_INT : Enc_NEGINT , count)) {
        Py_DECREF(work);
        return -1;
    }
    
    int ret = JSON_Accu_Accumulate(rval, (unsigned char*)PyString_AS_STRING(work), PyString_GET_SIZE(work));
    Py_DECREF(work);
    return ret;
}

static const double pow10[] = {1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000};

static void strreverse(char* begin, char* end)
{
    char aux;
    while (end > begin) {
        aux = *end, *end-- = *begin, *begin++ = aux;
    }
}

unsigned char dtoa(double value, char* str)
{
    static const int prec = 9;
    if (!endian) {
        fix_special_floats();
    }

    if (value == inf_value) {
        return Enc_INF;
    }
    if (value == neginf_value) {
        return Enc_NEGINF;
    }
    if (value == nan_value || !(value == value)) {
        return Enc_NAN;
    }
    
    /* if input is larger than thres_max, revert to exponential */
    const double thres_max = (double)(0x7FFFFFFF);
    
    int count;
    double diff = 0.0;
    char* wstr = str;
    
    /* we'll work in positive values and deal with the
     negative sign issue later */
    int neg = 0;
    if (value < 0) {
        neg = 1;
        value = -value;
    }
    
    
    int whole = (int) value;
    double tmp = (value - whole) * pow10[prec];
    uint32_t frac = (uint32_t)(tmp);
    diff = tmp - frac;
    
    if (diff > 0.5) {
        ++frac;
        /* handle rollover, e.g.  case 0.99 with prec 1 is 1.0  */
        if (frac >= pow10[prec]) {
            frac = 0;
            ++whole;
        }
    } else if (diff == 0.5 && ((frac == 0) || (frac & 1))) {
        /* if halfway, round up if odd, OR
         if last digit is 0.  That last part is strange */
        ++frac;
    }
    
    /* for very large numbers switch back to native sprintf for exponentials.
     anyone want to write code to replace this? */
    /*
     normal printf behavior is to print EVERY whole number digit
     which can be 100s of characters overflowing your buffers == bad
     */
    if (value > thres_max) {
        sprintf(str, "%e", neg ? -value : value);
        if (str[0] == 'n') {
            return Enc_NAN;
        }
        if (str[0] == 'i') {
            return Enc_INF;
        }
        if (str[0] == '-' && str[1] == 'i') {
            return Enc_NEGINF;
        }
        return Enc_FLOAT;
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
        
        //vvvvvvvvvvvvvvvvvvv  Diff from modp_dto2
    } else if (frac) {
        count = prec;
        // now do fractional part, as an unsigned number
        // we know it is not 0 but we can have leading zeros, these
        // should be removed
        while (!(frac % 10)) {
            --count;
            frac /= 10;
        }
        //^^^^^^^^^^^^^^^^^^^  Diff from modp_dto2
        
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
    *wstr='\0';
    strreverse(str, wstr-1);
    return Enc_FLOAT;
}

static int
encode_float_from_charstring(JSON_Accu *rval, const char* str, int len, unsigned char token)
{
    int rv = -1;
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
        for (int i=0; i<len && !rv; i++) {
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
encode_float(JSON_Accu *rval, PyObject *obj)
{
    char buffer[0x80];
    double d = PyFloat_AS_DOUBLE(obj);
    unsigned char token = dtoa(d, buffer);
    return encode_float_from_charstring(rval, buffer, strlen(buffer), token);
}

static int
encode_decimal(JSON_Accu *rval, PyObject *obj)
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
encode_key(JSON_Accu *rval, PyObject *obj)
{
    PyObject *encoded = NULL;
    PyObject *value = NULL;
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
    int len = PyString_GET_SIZE(encoded);
    unsigned char clen = (unsigned char)len;
    if (len > 127 || JSON_Accu_Accumulate(rval, &clen, 1)) {
        Py_DECREF(encoded);
        return -1;
    }
    int ret = JSON_Accu_Accumulate(rval, (unsigned char*)PyString_AS_STRING(encoded), PyString_GET_SIZE(encoded));
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
check_circular(JSON_Accu *rval, PyObject *obj, PyObject **ident_ptr)
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
encoder_listencode_obj(PyEncoderObject *s, JSON_Accu *rval, PyObject *obj)
{
    /* Encode Python object obj to a JSON term, rval is a PyList */
    int rv = -1;
    do {
        if (obj == Py_None || obj == Py_True || obj == Py_False) {
            unsigned char c = obj == Py_False ? 0 : obj == Py_True ? 1 : 2;
            rv = JSON_Accu_Accumulate(rval, &c, 1);
        }
        else if (PyUnicode_Check(obj))
        {
            PyObject *encoded = PyUnicode_AsUTF8String(obj);
            if (encoded != NULL) {
                rv = encode_type_and_content(rval, Enc_STRING, (unsigned char*)PyString_AS_STRING(encoded), PyString_GET_SIZE(encoded));
            }
        }
#if PY_MAJOR_VERSION >= 3
        else if (PyBytes_Check(obj))
        {
            rv = encode_type_and_content(rval, Enc_BINARY, (unsigned char*)PyBytes_AS_STRING(obj), PyBytes_GET_SIZE(obj));
        }
#else
        else if (PyString_Check(obj))
        {
            rv = encode_type_and_content(rval, Enc_STRING, (unsigned char*)PyString_AS_STRING(obj), PyString_GET_SIZE(obj));
        }
        else if (PyInt_Check(obj)) {
            rv = encode_long_no_overflow(rval, PyInt_AS_LONG(obj));
        }
#endif
        else if (PyLong_Check(obj)) {
            rv = encode_long(rval, obj);
        }
        else if (PyFloat_Check(obj)) {
            rv = encode_float(rval, obj);
        }
        else if (s->for_json && _has_for_json_hook(obj)) {
            PyObject *newobj;
            if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                return rv;
            newobj = PyObject_CallMethod(obj, "for_json", NULL);
            if (newobj != NULL) {
                rv = encoder_listencode_obj(s, rval, newobj);
                Py_DECREF(newobj);
            }
            Py_LeaveRecursiveCall();
        }
        else if (_is_namedtuple(obj)) {
            PyObject *newobj;
            if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                return rv;
            newobj = PyObject_CallMethod(obj, "_asdict", NULL);
            if (newobj != NULL) {
                rv = encoder_listencode_dict(s, rval, newobj);
                Py_DECREF(newobj);
            }
            Py_LeaveRecursiveCall();
        }
        else if (PyDict_Check(obj)) {
            if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                return rv;
            rv = encoder_listencode_dict(s, rval, obj);
            Py_LeaveRecursiveCall();
        }
        else if (PyObject_TypeCheck(obj, (PyTypeObject *)s->Decimal)) {
            rv = encode_decimal(rval, obj);
        }
        else if (PyObject_Length(obj) >= 0) {
            if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                return rv;
            rv = encoder_listencode_list(s, rval, obj);
            Py_LeaveRecursiveCall();
        }
        else {
            PyErr_Clear();
            if (Py_EnterRecursiveCall(" while encoding a JSON object"))
                return rv;
            PyObject *iter = PyObject_GetIter(obj);
            if (iter) {
                rv = encoder_listencode_sequence(s, rval, iter);
                Py_XDECREF(iter);
            } else {
                PyObject *ident = NULL;
                PyObject *newobj;
                if (s->check_circular && check_circular(rval, obj, &ident)) {
                    break;
                }
                PyErr_Clear();
                newobj = PyObject_CallFunctionObjArgs(s->defaultfn, obj, NULL);
                if (newobj) {
                    rv = encoder_listencode_obj(s, rval, newobj);
                    Py_DECREF(newobj);
                }
                if (rv) {
                    rv = -1;
                }
                else if (ident != NULL) {
                    if (PyDict_DelItem(rval->markers, ident)) {
                        rv = -1;
                    }
                }
                Py_XDECREF(ident);
            }
            Py_LeaveRecursiveCall();
        }
    } while (0);
    return rv;
}

static int
encoder_listencode_dict(PyEncoderObject *s, JSON_Accu *rval, PyObject *dct)
{
    /* Encode Python dict dct a JSON term */
    PyObject *kstr = NULL;
    PyObject *ident = NULL;
    PyObject *iter = NULL;
    PyObject *item = NULL;
    PyObject *items = NULL;
    PyObject *encoded = NULL;
    Py_ssize_t idx;

    int len = PyDict_Size(dct);
    if (encode_type_and_length(rval, Enc_DICT, len)) {
        return -1;
    }

    if (len) {
        if (s->check_circular && check_circular(rval, dct, &ident)) {
            goto bail;
        }
        
        iter = encoder_dict_iteritems(s, dct);
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

            encoded = rval->key_memo ? PyDict_GetItem(rval->key_memo, key) : NULL;
            if (encoded != NULL) {
                long value = PyLong_AS_LONG(encoded);
                unsigned char l = 0x80 | (unsigned char)value;
                if (JSON_Accu_Accumulate(rval, &l, 1)) {
                    goto bail;
                }
            } else if (encode_key(rval, key)) {
                goto bail;
            }
            if (encoder_listencode_obj(s, rval, value))
                goto bail;
            Py_CLEAR(item);
            idx += 1;
        }
        Py_CLEAR(iter);
        if (PyErr_Occurred())
            goto bail;
        if (ident != NULL) {
            if (PyDict_DelItem(rval->markers, ident))
                goto bail;
            Py_CLEAR(ident);
        }
        return 0;
    }

bail:
    Py_XDECREF(encoded);
    Py_XDECREF(items);
    Py_XDECREF(iter);
    Py_XDECREF(kstr);
    Py_XDECREF(ident);
    return -1;
}


static int
encoder_listencode_list(PyEncoderObject *s, JSON_Accu *rval, PyObject *seq)
{
    /* Encode Python list seq to a JSON term */
    PyObject *iter = NULL;
    PyObject *obj = NULL;
    PyObject *ident = NULL;
    int len = PyObject_Length(seq);
    if (encode_type_and_length(rval, Enc_LIST, len)) {
        return -1;
    }

    if (len) {
        if (s->check_circular && check_circular(rval, seq, &ident)) {
            goto bail;
        }
        
        iter = PyObject_GetIter(seq);
        if (iter == NULL)
            goto bail;
        
        while ((obj = PyIter_Next(iter))) {
            if (encoder_listencode_obj(s, rval, obj))
                goto bail;
            Py_CLEAR(obj);
        }
        Py_CLEAR(iter);
        if (PyErr_Occurred())
            goto bail;
        if (ident != NULL) {
            if (PyDict_DelItem(rval->markers, ident))
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
encoder_listencode_sequence(PyEncoderObject *s, JSON_Accu *rval, PyObject *iter)
{
    /* Encode Python list seq to a JSON term */
    PyObject *obj = NULL;
    
    unsigned char c = Enc_TERMINATED_LIST;
    if (JSON_Accu_Accumulate(rval, &c, 1))
        return -1;

    while ((obj = PyIter_Next(iter))) {
        int rv = encoder_listencode_obj(s, rval, obj);
        Py_XDECREF(obj);
        if (rv) {
            return -1;
        }
    }
    if (PyErr_Occurred())
        return -1;
    c = Enc_TERMINATOR;
    if (JSON_Accu_Accumulate(rval, &c, 1))
        return -1;
    return 0;
}

static void
encoder_dealloc(PyObject *self)
{
    /* Deallocate Encoder */
    encoder_clear(self);
    Py_TYPE(self)->tp_free(self);
}

static int
encoder_traverse(PyObject *self, visitproc visit, void *arg)
{
    PyEncoderObject *s;
    assert(PyEncoder_Check(self));
    s = (PyEncoderObject *)self;
    Py_VISIT(s->defaultfn);
    Py_VISIT(s->sort_keys);
    Py_VISIT(s->item_sort_kw);
    Py_VISIT(s->Decimal);
    return 0;
}

static int
encoder_clear(PyObject *self)
{
    /* Deallocate Encoder */
    PyEncoderObject *s;
    assert(PyEncoder_Check(self));
    s = (PyEncoderObject *)self;
    Py_CLEAR(s->defaultfn);
    Py_CLEAR(s->skipkeys_bool);
    Py_CLEAR(s->sort_keys);
    Py_CLEAR(s->item_sort_kw);
    Py_CLEAR(s->Decimal);
    return 0;
}

PyDoc_STRVAR(encoder_doc, "_iterencode(obj) -> iterable");

static
PyTypeObject PyEncoderType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pbjson._speedups.Encoder",       /* tp_name */
    sizeof(PyEncoderObject), /* tp_basicsize */
    0,                    /* tp_itemsize */
    encoder_dealloc, /* tp_dealloc */
    0,                    /* tp_print */
    0,                    /* tp_getattr */
    0,                    /* tp_setattr */
    0,                    /* tp_compare */
    0,                    /* tp_repr */
    0,                    /* tp_as_number */
    0,                    /* tp_as_sequence */
    0,                    /* tp_as_mapping */
    0,                    /* tp_hash */
    encoder_call,         /* tp_call */
    0,                    /* tp_str */
    0,                    /* tp_getattro */
    0,                    /* tp_setattro */
    0,                    /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,   /* tp_flags */
    encoder_doc,          /* tp_doc */
    encoder_traverse,     /* tp_traverse */
    encoder_clear,        /* tp_clear */
    0,                    /* tp_richcompare */
    0,                    /* tp_weaklistoffset */
    0,                    /* tp_iter */
    0,                    /* tp_iternext */
    0,                    /* tp_methods */
    encoder_members,      /* tp_members */
    0,                    /* tp_getset */
    0,                    /* tp_base */
    0,                    /* tp_dict */
    0,                    /* tp_descr_get */
    0,                    /* tp_descr_set */
    0,                    /* tp_dictoffset */
    encoder_init,         /* tp_init */
    0,                    /* tp_alloc */
    encoder_new,          /* tp_new */
    0,                    /* tp_free */
};

static PyMethodDef speedups_methods[] = {
    {"decode",
        (PyCFunction)py_decode,
        METH_VARARGS,
        pydoc_decode},
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
    PyEncoderType.tp_new = PyType_GenericNew;
    if (PyType_Ready(&PyEncoderType) < 0)
        return NULL;

#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&moduledef);
#else
    m = Py_InitModule3("_speedups", speedups_methods, module_doc);
#endif
    Py_INCREF((PyObject*)&PyEncoderType);
    PyModule_AddObject(m, "make_encoder", (PyObject*)&PyEncoderType);
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
