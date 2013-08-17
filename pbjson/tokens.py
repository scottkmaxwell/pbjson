FALSE = 0
Enc_FALSE = b'\x00'
TRUE = 1
Enc_TRUE = b'\x01'
NULL = 2
Enc_NULL = b'\x02'
INF = 3
Enc_INF = b'\x03'
NEGINF = 4
Enc_NEGINF = b'\x04'
NAN = 5
Enc_NAN = b'\x05'
TERMINATED_LIST = 0x0c
Enc_TERMINATED_LIST = b'\x0c'
CUSTOM = 0x0e
Enc_CUSTOM = b'\x0e'
TERMINATOR = 0x0f
Enc_TERMINATOR = b'\x0f'
INT = 0x20
NEGINT = 0x40
FLOAT = 0x60
STRING = 0x80
BINARY = 0xA0
LIST = 0xC0
DICT = 0xE0

FltEnc_Plus = 0xa
FltEnc_Minus = 0xb
FltEnc_Decimal = 0xd
FltEnc_E = 0xe

float_encode = {
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    '+': FltEnc_Plus,
    '-': FltEnc_Minus,
    '.': FltEnc_Decimal,
    'e': FltEnc_E,
    'E': FltEnc_E
}

float_decode = dict((v, k) for k, v in float_encode.items())
