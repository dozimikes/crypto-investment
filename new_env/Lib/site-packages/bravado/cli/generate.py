# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse


def add_parser(subparsers, parents=[]):
    parser = subparsers.add_parser(
        'generate',
        parents=parents,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        help='Generate a SwaggerClient subclass for a given Swagger spec',
    )
    parser.add_argument(
        'path',
        help='Absolute or relative path of the swagger spec.',
    )
    parser.set_defaults(func=main)


def main(args):
    validate(args.path, args.force_owners_definition)
    print('Validation successful')