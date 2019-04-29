r"""Command-line tool to convert between JSON and Packed Binary JSON

Usage::

    $ echo '{"json":"obj"}' | python -m pbjson.tool
    ?json?obj

    $ echo '{ 1.2:3.4}' | python -m pbjson.tool
    Expecting property name: line 1 column 2 (char 2)

"""
import sys
import pbjson
import argparse
import pprint
from collections import OrderedDict

try:
    # noinspection PyPackageRequirements
    import simplejson as json
    does_unicode = True
except ImportError:
    import json
    does_unicode = False
try:
    import yaml
    try:
        from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
        from yaml import Loader, Dumper
    from yaml.representer import SafeRepresenter
    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG

    if sys.version_info[0] < 3:
        def dict_representer(dumper, data):
            return dumper.represent_dict(data.iteritems())
    else:
        def dict_representer(dumper, data):
            return dumper.represent_dict(data.items())


    def dict_constructor(loader, node):
        return OrderedDict(loader.construct_pairs(node))


    Dumper.add_representer(OrderedDict, dict_representer)
    Loader.add_constructor(_mapping_tag, dict_constructor)

    Dumper.add_representer(str, SafeRepresenter.represent_str)

    if sys.version_info[0] < 3:
        Dumper.add_representer(unicode, SafeRepresenter.represent_unicode)
except Exception:
    yaml = None


def main():
    parser = argparse.ArgumentParser(
        description='Convert between pbjson and json',
        epilog='If converting a PBJSON file with binary elements, you may need to use `--repr` since JSON cannot handle binary data.')
    parser.add_argument('-r', '--repr', action='store_true', help='instead of converting to JSON, just output the `repr` of the object')
    parser.add_argument('-p', '--pretty', action='store_true', help='make it nice for humans')
    if yaml is not None:
        parser.add_argument('-y', '--yaml', action='store_true', help='input or output is YAML instead of JSON')
    parser.add_argument('infile', nargs='?', type=argparse.FileType('rb'), default=sys.stdin, help='filename to convert from or to pbjson (default: stdin)')
    parser.add_argument('outfile', nargs='?', type=argparse.FileType('wb'), default=sys.stdout, help='filename to write the converted file to (default: stdout)')
    args = parser.parse_args()

    contents = args.infile.read()
    try:
        text = contents.decode()
    except Exception:
        text = None

    if text:
        if yaml is not None and args.yaml:
            try:
                obj = yaml.load(text, Loader=Loader)
            except ValueError:
                raise SystemExit(sys.exc_info()[1])
        else:
            try:
                obj = json.loads(text, object_pairs_hook=OrderedDict)
            except ValueError:
                if yaml is None:
                    raise SystemExit(sys.exc_info()[1])
                try:
                    obj = yaml.load(text, Loader=Loader)
                except ValueError:
                    raise SystemExit(sys.exc_info()[1])
        pbjson.dump(obj, args.outfile)
    else:
        try:
            obj = pbjson.loads(contents, document_class=OrderedDict)
        except ValueError:
            raise SystemExit(sys.exc_info()[1])
        if yaml is not None and args.yaml:
            j = yaml.dump(obj, Dumper=Dumper)
        elif args.repr:
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
