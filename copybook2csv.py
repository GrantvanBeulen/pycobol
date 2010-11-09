#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = """COBOL Copybook Parser ver 0.2

License: GPLv3, Copyright (C) 2010 Brian Peterson
This is free software.  There is NO warranty; 
not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
"""

USAGE = """copybook2csv.py FILE"""

import re, string, sys

class PictureString:

    REPEATS_RE = re.compile(r'(.)\((\d+)\)')
    FLOAT_RE = re.compile(r'S?[9Z]*[.V][9Z]+')
    INTEGER_RE = re.compile(r'S?[9Z]+')
    COMP_TYPES = ['Integer', 'Float', 'Double', 'BCD']

    def expand_repeat_chars(self, pic_str):
        while True:
            match = self.REPEATS_RE.search(pic_str)
            if not match:
                break
            expanded_str = match.group(1) * int(match.group(2))
            pic_str = self.REPEATS_RE.sub(expanded_str, pic_str, 1)
        return pic_str

    def parse(self, pic_str, comp=0):
        pic_str = self.expand_repeat_chars(pic_str)
        if comp:
            data_type = self.COMP_TYPES[int(comp)]
        elif self.FLOAT_RE.match(pic_str):
            data_type = 'Float'
        elif self.INTEGER_RE.match(pic_str):
            data_type = 'Integer'
        else:
            data_type = 'Char'
        decimal_pos = 0
        if 'V' in pic_str:
            decimal_pos = pic_str.index('V') + 1
            pic_str = pic_str.replace('V', '')
        result = (data_type, len(pic_str), decimal_pos)  
        return result


class Field:

    FIELD_PTRN = r'^(?P<level>\d{2})\s+(?P<name>\S+)'
    PIC_PTRN = r'\s+PIC\s+(?P<pic>\S+)'
    DEPENDING_ON_PTRN = r'\s+OCCURS.*DEPENDING ON (?P<occurs>\S+)'
    OCCURS_PTRN = r'\s+OCCURS (?P<occurs>\d+) TIMES'
    COMP_PTRN = r'\s+COMP-(?P<comp>[1-3])'
    FIELD_RE = [ re.compile(i + '.') for i in [
        FIELD_PTRN + PIC_PTRN + COMP_PTRN,
        FIELD_PTRN + DEPENDING_ON_PTRN,
        FIELD_PTRN + OCCURS_PTRN + PIC_PTRN + COMP_PTRN,
        FIELD_PTRN + OCCURS_PTRN + PIC_PTRN,
        FIELD_PTRN + OCCURS_PTRN,
        FIELD_PTRN + PIC_PTRN,
        FIELD_PTRN
    ] ]
    FIELDS = ['occurs', 'level', 'name', 'type', 'length', 'decimal_pos', 'pic', 'comp']
    pic = PictureString()

    def parse(self, line_num, line):
        fields = { 'name': '', 'level': '0', 'occurs': '1', 'comp': '0' }
        pattern_num, num_patterns = 0, len(self.FIELD_RE)
        while pattern_num < num_patterns:
            match = self.FIELD_RE[pattern_num].match(line)
            if match:
                for key, value in match.groupdict().items():
                    fields[key] = value
                break
            pattern_num += 1
        result = [ fields[i] for i in self.FIELDS[:3] ]
        if 'pic' in fields:
             result += self.pic.parse(fields['pic'], int(fields['comp']))
        return result


class Copybook:

    LEGAL_DB_NAME_RE = re.compile(r'[^\w*+]')
    OCCURS, LEVEL, NAME = range(3)

    def legalize_db_name(self, name, camel_case=False):
        name = self.LEGAL_DB_NAME_RE.sub('_', name)
        if camel_case:
            return ''.join([ i.capitalize() for i in name.split('_') ])
        return name.lower()

    def set2legal_db_names(self):
        result = []
        for field in self.fields:
            field = list(field)
            if len(field) <= 3:
                field[self.NAME] = self.legalize_db_name(field[self.NAME], True)
                if not field[self.OCCURS].isdigit():
                    field[self.OCCURS] = self.legalize_db_name(field[self.OCCURS])
            else:
                field[self.NAME] = self.legalize_db_name(field[self.NAME])
            result.append(field)
        self.fields = result

    def occurs_n_times(self):
        levels = [0]
        for field in self.fields:
            line = ''
            level = int(field[self.LEVEL])
            if level == 1:
                line = field[self.NAME]
            if level <= levels[-1]:
                levels.pop()
            tabs = '\t' * (len(levels) - 1)
            if len(field) > 3:
                line = ', '.join([ str(i) for i in field[self.NAME:] ])
            elif field[self.OCCURS] != '1':
                line = '{0[2]} OCCURS {0[0]!r} TIMES:'.format(field)
                levels.append(level)
            if line:
                sys.stdout.write(tabs + line + '\n')

    def parse(self, lines):
        lines = [ i.strip() for i in lines ]
        lines = [ i for i in lines if i ]
        lines = [ i for i in lines if i[0] != '*' ]
        field = Field()
        self.fields = [ field.parse(i, j) for i, j in enumerate(lines) ]
        self.set2legal_db_names()
        self.occurs_n_times()


    def camel_case(self, name):
        return ''.join([ i.title() for i in name.split('_') ])


def main(args):
    Copybook().parse(args.copybook.readlines())

if __name__ == '__main__':
    from cmd_line_args import Args
    args = Args(USAGE, __version__)
    args.allow_stdin()
    args.add_files('copybook')
    main(args.parse())


