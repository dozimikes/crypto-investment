# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import sys

from pkg_resources import get_distribution

import bravado.cli.generate


CLI_MODULES = frozenset([
    bravado.cli.generate,
])


def _parser():
    parser = argparse.ArgumentParser(
        description='The bravado command line interface.',
        epilog='Run \'bravado <command> --help\' for more information on a command.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=get_distribution('bravado').version,
    )

    parent_parser = argparse.ArgumentParser(add_help=False)
    subparsers = parser.add_subparsers()
    parent_parsers = [parent_parser]
    for tool_cli_module in CLI_MODULES:
        tool_cli_module.add_parser(subparsers, parents=parent_parsers)

    return parser


def _main(argv):
    args = _parser().parse_args(argv[1:])
    return args.func(args)


def main():
    sys.exit(_main(sys.argv))


if __name__ == '__main__':
    main()
