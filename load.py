"""READ IN TEXT, LINES or CSV DATA
High-level functions to read in text, lines or CSV data with support for iterative stripping & pruning.

Supports ASCII files in the following formats:
    - text (returns text as string)
    - lines (returns list of line strings)
    - CSV (returns list of lists of fields)

Supports the following iterative stripping & pruning options:
    - lines
        - left and/or right 'strip' each line
        - 'prune' each line that is empty
    - csv_
        - 'strip' each CSV token
        - 'prune' each line where all CSV tokens are empty

Examples:
load.text('file1.txt')
load.lines('file1.txt', stop_at=5)
load.csv_('file1.txt', strip=True, prune=True)
"""

__version__ = """load ver 0.5

Copyright (C) 2010 Brian Peterson
This is free software; see source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
"""
import csv, sys

def text(file_name, fmt='text', sep=',', stop_at_line=None):
    """LOAD TEXT FILE
    file_name:
        - (file): file handle
        - (string): file name
    fmt (string):
        - 'text': reads in file as string, contains EOL characters
        - 'lines': reads in file as a list of lines
        -'csv': reads in a delimited text file as list of lists
    sep (string) - delimiter in CSV files
    stop_at_line (none or integer)  - line num to stop reading file,
        only applies to 'lines' & 'csv' formats
    returns:
        - (string) fmt:'text'
        - (list of strings) fmt:'lines'
        - (list of lists of strings) fmt:'csv'
        - (none) error opening or reading file
    """
    if type(file_name) is file:
        f = file_name
    else:
        try:
            f = open(file_name)
        except IOError, error_msg:
            sys.stderr.write('load.text: ERROR loading file "%s".\n%s\n' % (file_name, error_msg))
            return
    try:
        if fmt == 'lines':
            if stop_at_line is None:
                result = f.readlines()
            elif stop_at_line < 0:
                sys.stderr.write('load.py: ERROR - ')
                sys.stderr.write('stop_at_line parameter must be a positive integer\n')
                sys.exit(1)
            else:
                result = [ f.readline() for line in range(stop_at_line) ]
        elif fmt == 'csv':
            result = list(csv.reader(f, delimiter=sep))
            if stop_at_line is not None:
                result = result[:stop_at_line]
        else:
            result = f.read()
    finally:
        try:
            f.close()
        except:
            pass
    return result

def lines(file_name, strip_=False, strip_chars=None, prune=False, stop_at_line=None):
    """Load lines from file into a list
    file_name:
        - (file): file handle
        - (string): file name
    strip_:
        - (boolean) True: strip whitespace from left & right-side
        - (string) 'l' or 'left': strip whitespace from left-side
        - (string) 'r' or 'right': strip whitespace from right-side
    strip_chars:  
        - (none): Whitespace
        - (string of chars):
    prune (boolean) - remove blank lines
    stop_at_line (int) - line number at which to stop reading file
    returns (list of strings) - lines without EOL chars
    """
    lines = text(file_name, 'lines', stop_at_line=stop_at_line)
    if strip_:
        lines = [ line.strip(strip_chars) for line in lines ]
    elif type(strip_) is str:
        if len(strip_):
            if strip_[0] == 'l':
                lines = [ line.lstrip(strip_chars) for line in lines ]
            elif strip_[0] == 'r':
                lines = [ line.rstrip(strip_chars) for line in lines ]               
    if prune is True:
        lines = [ line for line in lines if line ]
    return lines  
   
def csv_(file_name, sep=',', strip_= False, strip_chars=None, prune=False, stop_at_line=None):
    """Load Comma Separated Values (CSV) from file
    file_name:
        - (file): file handle
        - (string): file name
    strip_:
        - (boolean) True: strip whitespace from left & right-side
        - (string) 'l' or 'left': strip whitespace from left-side
        - (string) 'r' or 'right': strip whitespace from right-side
    strip_chars:  
        - (none): Whitespace
        - (string of chars):
    prune (boolean) - remove lines where all tokens are empty
    stop_at_line (int) - line number at which to stop reading file
    returns (list of lists of strings) - lines as a list of fields (tokens)
    """
    if type(file_name) is str:
        lines = text(file_name, 'csv', sep)
    else:
        lines = list(csv.reader(file_name, delimiter=sep))
    if strip_:
        result = []
        if strip_ is True:
            for line in lines:
                result.append([ i.strip(strip_chars) for i in line ])
        elif type(strip_) is str:
            if len(strip_):
                if strip_[0] == 'l':
                    for line in lines:
                        result.append([ i.lstrip(strip_chars) for i in line ])
                elif strip_[0] == 'r':
                    for line in lines:
                        result.append([ i.rstrip(strip_chars) for i in line ])
                else:
                    result = lines
            else:
                result = lines
        lines = result
    if prune:
        lines = [ line for line in lines if ''.join(line) ]
    return lines
