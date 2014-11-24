r"""Command-line tool to convert between JSON and Packed Binary JSON

Usage::

    $ echo '{"json":"obj"}' | python -m pbjson.tool
    ?json?obj

    $ echo '{ 1.2:3.4}' | python -m pbjson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import sys
try:
    # noinspection PyPackageRequirements
    import simplejson as json
    does_unicode = True
except ImportError:
    import json
    does_unicode = False
import pbjson
import argparse
import pprint
from collections import OrderedDict


def main():
    parser = argparse.ArgumentParser(
        description='Convert between pbjson and json',
        epilog='If converting a PBJSON file with binary elements, you may need to use `--repr` since JSON cannot handle binary data.')
    parser.add_argument('-r', '--repr', action='store_true', help='instead of converting to JSON, just output the `repr` of the object')
    parser.add_argument('-p', '--pretty', action='store_true', help='make it nice for humans')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='filename to convert from or to pbjson (default: stdin)')
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('wb'), default=sys.stdout, help='filename to write the converted file to (default: stdout)')
    args = parser.parse_args()

    contents = args.infile.read()
    try:
        text = contents.decode()
    except Exception:
        text = None

    if text:
        try:
            obj = json.loads(text, object_pairs_hook=OrderedDict)
        except ValueError:
            raise SystemExit(sys.exc_info()[1])
        else:
            pbjson.dump(obj, args.outfile)
    else:
        try:
            obj = pbjson.loads(contents, document_class=OrderedDict)
        except ValueError:
            raise SystemExit(sys.exc_info()[1])
        if args.repr:
            j = pprint.pformat(obj, indent=1) if args.pretty else repr(obj)
        else:
            kw = {'ensure_ascii': False} if does_unicode else {}
            j = json.dumps(obj, sort_keys=True, indent=4 if args.pretty else None, **kw)
        if args.outfile == sys.stdout:
            j += '\n'
        else:
            j = j.encode()
        args.outfile.write(j)


if __name__ == '__main__':
    main()
