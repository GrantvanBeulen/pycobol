#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = """COBOL Fixed-length Data Parser ver 0.2
Note: This version does not work with OCCURS in Copybook files,
but is a lot faster than the varaible length data parser modules.

License: GPLv3, Copyright (C) 2010 Brian Peterson
This is free software.  There is NO warranty; 
not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
"""
USAGE = """copybook2list.py CopybookFile"""

import load
import csv, struct, sys

def parse_data(struct_fmt, lines):
    try:
      return [ struct.unpack(struct_fmt, i) for i in lines ]
    except struct.error:
        sys.stderr.write('Record layout vs. record size mismatch\n')
        size = sum([ int(i) for i in struct_fmt.split('s')[:-1] ])
        return [ struct.unpack(struct_fmt, i.ljust(size)[:size]) 
          for i in lines ]

def main(args):  
    copybook = load.csv_(args.copybook.readlines(), strip_=True)[1:]
    field_lengths = [ int(i[2]) for i in copybook ]
    struct_fmt = 's'.join([ str(i) for i in field_lengths ]) + 's'
    if args.struct:
        print struct_fmt
    else:
        for record in parse_data(struct_fmt, load.lines(args.datafile)):
            print record

if __name__ == '__main__':
    from cmd_line_args import Args
    args = Args(USAGE, __version__)
    args.allow_stdin()
    args.add_files('datafile', 'copybook')
    args.parser.add_argument('-s', '--struct', action='store_true',
        help='show structure format')
    main(args.parse())