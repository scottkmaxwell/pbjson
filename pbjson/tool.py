r"""Command-line tool to convert between JSON and Packed Binary JSON

Usage::

    $ echo '{"json":"obj"}' | python -m pbjson.tool
    ?json?obj

    $ echo '{ 1.2:3.4}' | python -m pbjson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
from __future__ import with_statement
import sys
import json
import pbjson
from collections import OrderedDict


def main():
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit(sys.argv[0] + " [infile [outfile]]")
    with infile:
        contents = infile.read()
        try:
            text = contents.decode()
        except Exception as e:
            text = None
        if text:
            try:
                obj = json.loads(text, object_pairs_hook=OrderedDict)
            except ValueError:
                raise SystemExit(sys.exc_info()[1])
            else:
                with outfile:
                    pbjson.dump(obj, outfile)
        else:
            try:
                obj = pbjson.loads(contents, document_class=OrderedDict)
            except ValueError:
                raise SystemExit(sys.exc_info()[1])
            else:
                with outfile:
                    json.dump(obj, outfile, sort_keys=True, indent='    ')
                    outfile.write('\n')


if __name__ == '__main__':
    main()
