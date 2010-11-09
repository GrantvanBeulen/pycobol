"""Python/Django-based COBOL data conversion tools
===============================================
"...built for comfort, I ain't a-built for speed... "
     - Willie Dixon

Uses copybook2csv.py output for file layout
Uses copybook2django.py output for database model
--------------------------------------------------
Parses COBOL fixed-width data file and populates
relational database.  Data is normalized.

For each record loops through fields in copybook2csv
Parsing out data from recordds one field at a time.
When a field endswith ':' it indicates the start of a loop
----------------------------------------------------------
:Version: 0.8
:Date: June 2010
:Copyright: 2010 Brian Peterson
----------------------------------------------------------
cobol2db.py is part of pyCobol 

pyCobol is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation.

pyCobol is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyCobol.  If not, see <http://www.gnu.org/licenses/>.

"""

VERSION = """COBOL-to-RDBMS ver 0.5\n\n
Copyright (C) 2010 Brian Peterson\n
This is free software; see source for copying conditions.  There is NO\n
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n
"""
import os.path
import re
import struct
import sys
import django.core.exceptions
from datetime import datetime

import load
import names
from xsplicer import Splice
from autosize import TextTable



# make sure DJANGO_SETTINGS_PATH is defined
# !!!!!! PROGRAM WILL NOT WORK UNTIL YOU CHANGE THE LINE BELOW !!!!!!
try:
  import <django-project-name>.<django-app-name>.models
except:
  pass

class Debug:
    """Dummy object used for debug mode"""
    def __init__(self, name):
        self.name = name

class Field:
    """Field definitions based on copybook2csv.py output"""
    def __init__(self, line):
        """Field constructor
        :type line: list 
        :param line: line from copybook2csv split at ','
             
        """
        self.value = None
        self.indents = line[0].count('\t')
        field = [ i.lstrip() for i in line ]
        if len(field) == 1:
            # it's a loop not a field, i.e. <name> OCCURS x TIMES
            self.name = field[0]
        else:
            # standard field definition
            name, self.type, length, decimal_pos = field
            self.name = names.legal_db_name(name)
            self.length = int(length) 
            self.decimal_pos = int(decimal_pos)
    
    def get_value(self, data):
        """Value type conversions
        :type data: string 
        :param data: field data string read from record  
           
        """
        data = data.strip()
        if self.type != 'Char' and not data:
            return None
        try:
            if self.type == 'Integer':
                data = int(data)
            elif self.type == 'Float':
                data = float(data)
            elif self.type == 'Double':
                data = double(data)
            if self.type in ['DateTime', 'Date', 'Time'] and data:
                if self.type == 'DateTime':
                    if len(data) == 12:
                        data = struct.unpack('4s2s2s2s2s', data) 
                        yr, mon, day, hr, min = [ int(i) for i in data ]
                        sec = 0
                    else:        
                        data =  struct.unpack('4s2s2s2s2s2s', data)
                        yr, mon, day, hr, min, sec = [ int(i) for i in data ]
                    data = datetime(yr, mon, day, hr, min, sec)
                    data = data.strftime('%Y-%m-%d %H:%M:%S').strip()
                elif self.type == 'Date':
                    if data == '00000000':
                        data = None
                    else:
                        data = struct.unpack('4s2s2s', data)
                        yr, mon, day = [ int(i) for i in data ]
                        data = datetime(yr, mon, day).strftime('%Y-%m-%d').strip()              
                elif self.type == 'Time':
                    if len(data) == 4:
                        data = struct.unpack('2s2s', data) 
                        hr, min = [ int(i) for i in data ]
                        sec = 0
                    else:                    
                        data =  struct.unpack('2s2s2s', data)
                        hr, min, sec = [ int(i) for i in data ]
                    data = datetime(2000, 1, 1, hr, min, sec)
                    data = data.strftime('%H:%M:%S').strip()
        except:
            return False
        return data
       
    def verbose(self):
        """Tuples used for generate verbose output"""
        if self.name.endswith(':'):
            return (self.indents, self.name)
        return (self.indents, self.name, self.type, self.length, 
            self.decimal_pos, self.value)  

class Loop:
    """OCCURS x TIMES"""
    def __init__(self, field_num, field):
        """Loop constructor
        If a word occurs before "OCCURS x TIMES", that word is
        used for the name of model, otherwise the name is determined
        from the base model name followed by and underscore and the
        line number at which the loop starts.
        
        Setup whether it is fixed loop or wheter it depends on another value
        
        :type field_num: list 
        :param field_num: line from copybook2csv split at ','   
        
        :type field: Field object
        :param field:   
        
        """
        self.counter = 0
        self.start_line_num = field_num
        loop_str = field.name.split()
        if loop_str[0] == 'OCCURS':
            loop_name = self.model_name
            self.name = '%s_%d' % (loop_name, field_num)
            self.num_times = loop_str[1]
        else:
            self.name, self.num_times = loop_str[0], loop_str[2]
        if self.num_times.isdigit():
            self.num_times = int(self.num_times)
            self.depends_on_field_name = False
        else:
            self.num_times = self.num_times.strip('"').strip("'")
            self.depends_on_field_name = names.legal_db_name(self.num_times)
            self.num_times = 0
         
    def loop_start(self, depend_ons):
        """Initiate a new loop, set loop counter to desired # of iterations
        
        :type depend_ons: dict (keys=field names)
        :param depend_ons: current field values that # of interations depend on
        
        """
        if self.num_times:
            self.counter = self.num_times
        else:
            self.counter = int(depend_ons[self.depends_on_field_name])
    
    def loop_next(self, field_num):
        """Done with last line of loop, ready for next iteration
        decrement loop counter, if counter=0 -> set end of loop flag, 
        else reset the field_num back to the 1st line of the loop
        
        :rtype: tuple (boolean, int)
        :returns:  end of loop flag, field # to continue parsing from
        
        """
        self.counter = max(0, self.counter - 1) 
        if self.counter:
            field_num = self.start_line_num
        return not self.counter, field_num

    def verbose(self):
        """tuples used for generate verbose output """
        return (self.start_line_num, self.name, self.num_times, 
            self.depends_on_field_name)


class Data:
    """COBOL record processing """
    
    HORIZ_SEP = '-' * 79
    HORIZ_DBL_SEP = '=' * 79
    
    def __init__(self, fields, records, args):
        """Data constructor
        :type fields: list of lists
        :param fields: CSV data read in from copybook2csv file 
                
        :type records: list
        :param records: list of data file lines
        
        :type model_name: string
        :param model_name: name of base model
        
        :type args: Namespace object
        :param args: command line arguments
        
        """
        self.MODELS = court.county_data.models
        self.records = records
        self.model_name = fields[0][0]
        self.fields = fields[1:]
        self.args = args
        self.active_models = []
    
    def disp_error_mesg(self, record_num, mesg, field=None, ch_pos=None):
        """Display error message       
        :type record_num: int
        :param record_num: record number (zero-indexed) where error ocurred
              
        :type mesg: string
        :param megs: error message
        
        :type field: Field object or None
        :param field: field where error occured or None hides field
        
        :type ch_pos: int or None
        :param ch_pos: character position in record or None hides field.
        
        """
        mesg = '%s\nERROR: %s.\n%s\n' % (self.HORIZ_DBL_SEP, mesg, 
            self.HORIZ_DBL_SEP)
        mesg += 'Record Number: %d\n' % (record_num + 1)
        if field is not None:
            mesg += 'Character Position:  %d\n' % (ch_pos + 1)
            field_str = ', '.join([ str(i) for i in field.verbose()[1:] ])
            mesg = '%sField: %s' % (mesg, field_str)
        sys.stderr.write('%s\n%s\n' % (mesg, self.HORIZ_DBL_SEP))

    def get_value(self, ch_pos, record_num, record, field):
        """Read field's data string from record, convert to proper data type
        move character position counter to point to beginning of next field        
        
        :type ch_pos: int
        :param ch_pos: current character position in record
        
        :type record_num: int
        :param record_num: record number (zero-indexed)
        
        :type record: string
        :param record: line in data file

        :type field: Field object
        :param field: current field to extract from record
        
        :rtype: tuple (int, char|int|float|double)
        :returns: next field's character position in record, value of field
        
        """
        record = self.records[record_num]
        if ch_pos + field.length > len(record) - 1:
            mesg = 'Field size exceeds length of data'
            self.disp_error_mesg(record_num, mesg, field, ch_pos)
            sys.exit(1)
        data = record[ch_pos:ch_pos + field.length]
        if field.decimal_pos:
            pos = field.length - field.decimal_pos
            data = '%s.%s' % (data[:pos], data[pos:])
        value = field.get_value(data)
        if value is False:
            mesg = 'Unable to convert %r to %s' % (data, field.type)
            self.disp_error_mesg(record_num, mesg, field, ch_pos)
            value = None
        return ch_pos + field.length, value

    def start_loop(self, loop, depend_ons):
        """Initialize new loop, set counter
        :type loop: Loop object
        :param loop: current loop
        
        :type depend_ons: dict (keys=field names)
        :param depend_ons: field values that # of interations depend on
        
        """
        loop.loop_start(depend_ons)


    
    def next_loop(self, args, record_num, field_num, loops):
        """Next iteration of loop, decrement counter
        :type field_num: int
        :param field_num: line number of current field, used to track 
            current position of parser, will be reset to beginning of
            loop if counter is not zero.
            
        :type loops: dict (keys=field_num)
        :param loops: dictionary of Loop objects, used to track & manage
            loop interations
        
        :rtype: tuple (boolean, int)
        :returns: end of loop flag (i.e. counter at 0), field number at 
            which to continue parsing
            
        """
        if self.args.verbose:
            print 'NEXT LOOP...'
        if self.args.ruler:
            print '-' * self.args.ruler    
        self.save_and_close_model(record_num)
        loop_line_num = max([ i for i in loops.keys()
            if i < field_num ])
        end_of_loop, field_num = loops[loop_line_num].loop_next(field_num) 
        if self.args.verbose:
            print 'END OF LOOP:', end_of_loop
            print 'FIELD_NUM:', field_num
        if not end_of_loop:
            self.active_models.append(self.new_model(loops[field_num].name))
        return end_of_loop, field_num, loops
    
    def new_model(self, name=None):
        """Create new instance of a Django Model
        :type name: string
        :param name: class name of Django Model
        
        """
        if not name:
            name = self.model_name
        if self.args.verbose:    
            print 'NEW MODEL: ', name
        if not self.args.debug:
            model_obj = getattr(self.MODELS, name)()
            return model_obj
        return Debug(name)

    def set_value_in_model(self, field_name, value):
        """Set field value in Django Model object
        :type field: string
        :param field: name of Model field
        
        :type value: char|int|float|double
        :param value: value to assign to field
        
        """
        if self.args.verbose:    
            print 'SETTING %r: %r TO %r' % (
                self.active_models[-1], field_name, value)
        elif self.args.values:
            print '%s%r' % (field_name.ljust(self.args.indent), value)
        if not self.args.debug:
            setattr(self.active_models[-1], field_name.lstrip('+*'), value)
        
    def save_and_close_model(self, rec_num):
        """Database insert/update 
        :type rec_num: int (zero-based)
        :param rec_num: record number - line # in data file
        
        """
        model = self.active_models.pop()
        if self.args.verbose:    
            print 'SAVE MODEL', model
        if not self.args.debug:
            try:
                model.save()
                print 'Saved record %d of %d... %s ... ID=%d' % (
                    rec_num + 1, self.num_records + 1, 
                    model.__class__.__name__, model.id)
            except django.core.exceptions.ValidationError as error_mesg: 
                mesg = '%r\n' % error_mesg
                mesg += 'Unable to save record in %s\n' % model.__class__.__name__
                self.disp_error_mesg(rec_num, mesg)
                sys.exit(1)
                
        if len(self.active_models):
            if self.args.verbose:    
                print 'MANY2MANY ADD: %r:%r' % (
                    self.active_models[-1].__class__.__name__, model)
            if not self.args.debug:
                try:
                    self.active_models[-1].save()
                except django.core.exceptions.ValidationError as error_mesg:
                    mesg = '%r\n' % error_mesg
                    text = 'Unable to save record in %s\n' % (
                        model.__class__.__name__[-1])
                    self.disp_error_mesg(rec_num, mesg)
                    sys.exit(1)
                name = model.__class__.__name__
                many2many_field = getattr(self.active_models[-1], name.lower())
                model_name = '%s_%s' % (
                    self.active_models[-1].__class__.__name__, 
                    model.__class__.__name__)
                try:
                    many2many_field.add(model)      
                except django.core.exceptions.ValidationError as error_mesg:
                    mesg = '%r\n' % error_mesg
                    mesg += 'Unable to save record in %s\n' % model_name
                    self.disp_error_mesg(rec_num, mesg)
                    sys.exit(1)

    def parse(self):
        """Parse COBOL data records"""
        fields = [ Field(i) for i in self.fields ]
        
        if self.args.fields:
            TextTable().show([ i.verbose() for i in fields ])
            legend = '\n(1)Indent-Level (2)Name (3)Type (4)Length'
            print legend + ' (5)Implied-Decimal-Position (6)Value'
            return
        
        loops = dict([ (i, Loop(i, j)) for i, j in enumerate(fields) 
            if j.name.endswith(':') ])
        if self.args.loops:
            TextTable().show([ i.verbose() for i in loops.values() ])
            return
            
        depend_ons = dict([ (i.depends_on_field_name, None) 
            for i in loops.values() if i.depends_on_field_name ])

        records = range(len(self.records))
        if args.recnum is not None:
            records = Splice().splice(self.args.recnum, records)
        record_num, self.num_records = records[0], records[-1]
        while record_num <= self.num_records:
            record = self.records[record_num]
            if 'data' in self.args:
                print record
            self.active_models = [ self.new_model() ]
            field_num, num_fields = 0, len(fields)
            ch_pos = last_indent = 0
            while field_num <= num_fields:
                if field_num == num_fields:
                    if loops:
                        end_of_loop, field_num, loops = self.next_loop(
                            args, record_num, field_num, loops)
                        if end_of_loop:
                            break
                    else:
                        break
                else:
                    field = fields[field_num]
                    if self.args.depends:
                        print 'DEPEND ONS:'
                        TextTable().show(depend_ons.items())
                    if self.args.verbose:
                        print '\nFIELD_NUM: ', field_num
                        print 'FIELD: ', self.fields[field_num]
                    end_of_loop = False
                    if field_num in loops.keys():
                        if self.args.verbose:
                            print 'START LOOP...'
                        if self.args.ruler:
                            print '-' * self.args.ruler   
                        self.start_loop(loops[field_num], depend_ons)
                        self.active_models.append(self.new_model(loops[field_num].name))
                    elif fields[field_num].indents < last_indent:
                        end_of_loop, field_num, loops = self.next_loop(
                            args, record_num, field_num, loops)
                    else:
                        if self.args.verbose:
                            output = 'UPDATE RECORD... CHAR POS: %r, LENGTH: %r'
                            print output % (ch_pos, field.length)
                        ch_pos, value = self.get_value(
                            ch_pos, record_num, record, field)
                        self.set_value_in_model(field.name, value)
                        if field.name in depend_ons:
                            # store value, will be used later for loop num_times dependency
                            depend_ons[field.name] = value
                last_indent = field.indents
                if not end_of_loop:
                    field_num += 1
                else:
                    if self.args.verbose:
                        print 'END OF LOOP...'
            while self.active_models:
                self.save_and_close_model(record_num)
            record_num += 1
            if self.args.ruler:
                print self.HORIZ_DBL_SEP
    

def get_base_model_name(filename):
    """Generates the name of the base model/table from the filename"""
    model_name = os.path.basename(filename)
    model_name = os.path.splitext(filename)
    model_name = names.legal_db_name(model_name[0]).title()
    return model_name

def main(args):
    fields = load.csv_(args.copybook, strip="right", prune=True)
    stop = None
    if args.recnum:
        stop = Splice().get_values(args.recnum)[1]
        if stop < 0:
            stop = None
    records = load.lines(args.datafile, stop_at_line=stop)
    Data(fields, records, args).parse()

if __name__ == '__main__':
    import argparse, argparse_ver
    usage = "cobol2rdbms.py COPYBOOK [DATAFILE]\n"
    usage += 'COPYBOOK - Filename: output from copybook2csv.py\n'
    usage += 'DATAFILE - Filename: COBOL records, fixed-width text'
    parser = argparse.ArgumentParser(usage=usage)
    parser.version = VERSION
    parser.add_argument('copybook', 
        help='filename... copybook2csv.py output')
    parser.add_argument('datafile', nargs='?', 
        help='filename... text file, COBOL fixed-width records')  
    parser.add_argument('-d', '--debug', action='store_true', 
        help='process without writing to database')  
    parser.add_argument('--depends', action='store_true',
        help='display depends on values')    
    parser.add_argument('--fields', action='store_true',
        help='display list of fields')    
    parser.add_argument('-i', '--indent', type=int, default=38,
        help='number of characters to indent when displaying field values, default=38')    
    parser.add_argument('--license', action='store_true', help='display license information')    
    parser.add_argument('--loops', action='store_true',
        help='display loops')    
    parser.add_argument('-r', '--recnum',
        help='record numbers to display, accepts splices, i.e. 3:5')    
    parser.add_argument('--ruler', type=int, default=78,
        help='length of horizontal ruler between loops & records, default=79, 0=disable')    
    parser.add_argument('-v', '--values', action='store_true', 
        help='display field values')  
    parser.add_argument('--verbose', action='store_true', 
        help='enable verbose mode')  
    parser.add_argument('-V', '--version', action=argparse_ver.VersionAction, 
        help='display version information and exit')
    args = parser.parse_args()
    if not sys.stdin.isatty():
        args.datafile = sys.stdin
    elif not args.datafile:
        parser.print_help()
        sys.exit()
    main(args)

      
