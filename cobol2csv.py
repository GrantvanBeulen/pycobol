__version__ = """COBOL Fixed-Length Record Parser ver 0.2
Note: This version does not support OCCURS in Copybook files

Copyright (C) 2010 Brian Peterson
This is free software; see source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
"""

USAGE = """cobol2csv.py COPYBOOK [DATAFILE]
COPYBOOK - Filename: output from copybook2csv.py
DATAFILE - Filename: COBOL records, fixed-width text
"""

import load
import re, struct, sys
from datetime import datetime
#from autosize import TextTable

HORIZ_LINE = '%s\n' % ('-' * 132)
DBL_HORIZ_LINE = '%s\n' % ('=' * 132)

class Field:
    """Parse field definitions from copybook2csv.py generated CSV file"""
    DATE_TIME_RE = re.compile(r'.*\(\'(.*?)\'\)')
    DATA_TYPE_RE = re.compile(r'[a-zA-Z]+')
    DATE_TIME_DATA_TYPES = ['DATETIME', 'DATE', 'TIME']
    SUPPORTED_DATA_TYPES = ['CHAR', 'INTEGER', 'FLOAT', 'DOUBLE']
    SUPPORTED_DATA_TYPES += DATE_TIME_DATA_TYPES
    
    def __init__(self, field_num, field_def, file_, datetime_output_fmt=None):
        """field_def (list of strings) - field definition items or loop info"""
        field_def = [ i.lstrip() for i in field_def ]
        if len(field_def) != 4: 
            self._error_invalid_format(field_def, file_)
        # 4-element field definition
        self.field_num = field_num
        self.name, data_type, length, decimal_pos = field_def
        # Copybook FILLER fields will filtered from the output
        self.is_filler = 'FILLER' in self.name.upper()
        # get data_type, base-type is the data-type without formatting info
        self.base_type = self.DATA_TYPE_RE.match(data_type).group().upper()
        if self.base_type not in self.SUPPORTED_DATA_TYPES:
            self._error_unsupported_data_type(field_def, file_)
        self.data_type = data_type
        try:
            self.length = int(length) 
            self.decimal_pos = int(decimal_pos)
        except:
            sys.stderr.write('Field type & length must be integers.\n')
            self._error_invalid_format()
        # date/time input format
        self.is_datetime = self.base_type in self.DATE_TIME_DATA_TYPES
        if self.is_datetime:
            self.datetime_input_fmt = self.DATE_TIME_RE.match(self.data_type)
            if not self.datetime_input_fmt:
                self._error_invalid_datetime_input_format()
        # date/time output format
        if datetime_output_fmt is None:
            self.datetime_output_fmt = FormatDateTimeOutput()
        elif isinstance(datetime_output_fmt, FormatDateTimeOutput):
            self.datetime_output_fmt = datetime_output_fmt
        else:
            self._error_invalid_datetime_output_object(datetime_output_fmt)

    def _error_unsupported_data_type(self, field_def, file_):    
        sys.stderr.write('ERROR: Invalid data-type.\n')
        sys.stderr.write('Field Name: %s\n' % self.name)
        sys.stderr.write('Data Type: %s\n' % self.base_type)
        sys.stderr.write('Supported Data Types:\n')
        supported_data_types = ', '.join(self.SUPPORTED_DATA_TYPES)
        sys.stderr.write('%s\n\n' % supported_data_types)
        self._error_invalid_format(field_def, file_)
       
    def _error_invalid_format(self, field_def, file_):
        sys.stderr.write('ERROR: Invalid Copybook field definition format.\n')
        mesg = 'Name, Data-Type, Length, Implied-Decimal-Position\n'
        sys.stderr.write('Required field format: ' + mesg)
        mesg = "Line #%d in file '%s'...\n"
        sys.stderr.write(mesg % (self.field_num + 1, file_.name))
        sys.stderr.write(HORIZ_LINE)        
        sys.stderr.write('%s\n' % ', '.join(field_def))
        sys.stderr.write(HORIZ_LINE)                
        sys.exit(1)

    def _error_invalid_datetime_input_format(self):
        sys.stderr.write('ERROR: Invalid %s input format.\n' % self.base_type)
        sys.stderr.write('Field Name: %s\n' % self.name)
        sys.stderr.write('Data Type: %s\n' % self.data_type)
        sys.exit(1)

    def _error_invalid_datetime_output_object(self, date_time_output_fmt):
        sys.stderr.write('ERROR: FormatDateTimeOutput object required.\n')
        mesg = 'Invalid datetime_output_fmt parameter in Field constructor.\n'
        sys.stderr.write(mesg)
        sys.stderr.write('Field Name: %s\n' % self.name)
        sys.exit(1)

    def get_value(self, record_num, field_data):
        """convert field strings to Copybook defined data-types"""
        field_data = field_data.strip()
        if self.base_type == 'CHAR':
            return field_data
        if self.decimal_pos:
            # insert implied decimal position
            data_chars = list(field_data)
            field_data = str(data_chars.insert(self.decimal_pos, '.'))
        try:
            if self.base_type == 'INTEGER':
                return int(field_data)
            if self.base_type == 'FLOAT':
                return float(field_data)
            if self.base_type == 'DOUBLE':    
                return double(field_data)
            if self.is_datetime:
                datetime_fmt_match = self.DATE_TIME_RE.match(self.data_type)
                if datetime_fmt_match:
                    dt_fmt = datetime_fmt_match.group(1)
                    time_tuple = datetime.strptime(field_data, dt_fmt)
                    result = self.datetime_output_fmt.convert(self.name, 
                        self.base_type, record_num, time_tuple, field_data)
                    return result
            else:
                self._error_undefined_type(record_num, field_data)
        except:
            self._error_data_type_conversion(record_num, field_data)

    def _error_data_type_conversion(self, record_num, field_data):    
        error_mesg = 'ERROR: Unable to convert string to %s.\n'
        sys.stderr.write(error_mesg  % self.data_type)
        sys.stderr.write('Record Number: %s\n' % record_num)
        sys.stderr.write('Field Name: %s\n' % self.name)
        sys.stderr.write('Record Data: %r\n' % field_data)
        sys.exit(1)
        
    def __str__(self):
        mesg = 'Name: %s, Type: %s, Length: %d, Implied-Decimal-Position: %d, ' 
        s = mesg % (self.name, self.data_type, self.length, self.decimal_pos)
        mesg = 'Base-Type: %s, Is DateTime?: %r, Is Filler?: %r'
        s += mesg % (self.base_type, self.is_datetime, self.is_filler)
        return s


class FormatDateTimeOutput:

    fmt = {}
    DATE_TIME_DATA_TYPES = ['DATETIME', 'DATE', 'TIME']

    def __init__(self, date_fmt='%Y-%m-%d', time_fmt='%H:%M:%S.%f', 
        datetime_fmt=None):
        self.fmt['DATE'] = self.set('DATE', date_fmt)
        self.fmt['TIME'] = self.set('TIME', time_fmt)
        if not datetime_fmt:
            self.fmt['DATETIME'] = self.set('DATETIME', '%s %s' % (
                date_fmt, time_fmt))
            
    def convert(self, field_name, data_type, record_num, datetime_obj, data):
        try:
            return datetime.strftime(datetime_obj, self.fmt[data_type])
        except:
            self._data_conversion_error(field_name, data_type, record_num, data)

    def set(self, data_type, fmt):
        data_type = data_type.upper()
        if data_type not in self.DATE_TIME_DATA_TYPES:
            self._data_type_error('N/A', data_type)
        self.fmt[data_type] = fmt
        try:
            datetime.strftime(datetime.today(), self.fmt[data_type])
        except:
            sys.stderr.write('ERROR: Unable to Set Date/Time Output Format - Invalid Format Specified.\n')
            self._data_conversion_error('N/A', data_type)
        return fmt

    def _data_type_error(self, field_name, data_type):
        mesg = 'ERROR: Invalid date/time data-type.\n'
        sys.stderr.write(mesg % repr(data_type))
        sys.stderr.write('Field Name: %s\n' % field_name)
        sys.stderr.write('Data Type: %s\n' % data_type)
        data_types = ', '.join(self.DATE_TIME_DATA_TYPES)
        sys.stderr.write('Valid Data-Types: %' % data_types)
        sys.exit(1)

    def _data_conversion_error(self, field_name, data_type, 
        record_num=0, data=None):
        sys.stderr.write('WARNING: Date/time conversion failed.\n')
        sys.stderr.write('Record Number: %r\n' % record_num)
        sys.stderr.write('Field Name: %r\n' % field_name)
        sys.stderr.write('Field Type: %r\n' % data_type)
        sys.stderr.write('Field Format: %r\n' % self.fmt[data_type])     
        sys.stderr.write('Record Data: %r\n' % data)
        sys.exit(1)


class Data:

    def __init__(self, fields, args, datetime_output_fmt=None):
        # -1 because 1st line in field def file is the structure/model name
        self.num_fields = len(fields) - 1
        if self.num_fields <= 0:
            self._error_incomplete_copybook_file(args.copybook)
        fields = enumerate(fields[1:])
        # convert each field entry into a field def object
        self.fields = [ Field(i, j, args.copybook, datetime_output_fmt)
            for i, j in fields ]
        # used for loop indexes
        self.field_idx = range(self.num_fields)
        self.field_names = ', '.join([ '"%s"' % i.name for i in fields ])
        self.field_lengths =  [ i.length for i in self.fields ]
        field_length_strings = [ str(i) for i in self.field_lengths ]
        # struct_str = fmt used by Python struct.unpack to parse data
        self.struct_str = 's'.join(field_length_strings) + 's'
        self.sum_of_field_lengths = sum(self.field_lengths)
        # running sum of field lengths, used for field-size/data-size
        # mismatches to determine field # where data is truncated.
        self.field_ends_at = self._cumulative_sum()
        if args.debug:
            self._debug()

    def _debug(self):
            sys.stdout.write('FIELDS:\n%s' % HORIZ_LINE)
            for field in self.fields:
                print field
    
    def _cumulative_sum(self):
        s = [self.field_lengths[0]]
        for field_num in range(1, len(self.field_lengths)):
            s.append(s[field_num - 1] + self.field_lengths[field_num])
        return s    

    def _error_incomplete_copybook_file(self, file_):
        sys.stderr.write('ERROR: Copybook file requires 2 lines minimum.\n')
        sys.stderr.write('1. First line must be the structure/model name.\n')
        sys.stderr.write('2. Followed by 1 or more field definition lines.\n')
        sys.stderr.write("File '%s'...\n" % (field_num + 1, file_.name))
        sys.stderr.write(HORIZ_LINE)        
        sys.stderr.write('%s\n' % ', '.join(field_def))
        sys.stderr.write(HORIZ_LINE)                
        sys.exit(1)
    
    def parse_record(self, record_num, record, debug):
        """Build struct fmt string and parse data (meat of the program)"""
        if not record:
            return
        struct_str = self.struct_str
        struct_mismatch = (self.sum_of_field_lengths != len(record))
        if struct_mismatch:
            lengths, record = self._warning_struct_mismatch(
                self.field_lengths, record)
            struct_str = 's'.join([ str(i) for i in self.field_lengths ]) + 's'
        if debug:
            sys.stdout.write("RECORD STRUCT FMT: '%s'\n" % struct_str)
            sys.stdout.write(HORIZ_LINE)
        data = struct.unpack(struct_str, record)
        data = [ self.fields[i].get_value(i + 1, data[i]) 
            for i in self.field_idx ]
        return ', '.join([ repr(i) for i in data ])

    def _warning_struct_mismatch(self, record_num, record):
        """mismatch: sum of field sizes not matching size of the data record"""
        struct_len = sum(self.field_lengths)
        record_len = len(record)
        sys.stderr.write('WARNING: ')
        sys.stderr.write('Sum of field lengths & record length mimatch.\n')
        sys.stderr.write('\tSum of field lengths: %d\n' % struct_len)
        sys.stderr.write('\tData record length: %d\n' % record_len)
        if struct_len < record_len:
            ignored_len = struct_len - record_len
            chars_ignored_mesg = '\t%d trailing characters ignored in record.\n' 
            sys.stderr.write(chars_ignored_mesg % ignored_len)
            sys.stderr.write(HORIZ_LINE)
            sys.stderr.write('%s\n' % record[:-ignored_len])
            sys.stderr.write(HORIZ_LINE)
            return field_lengths, record[:struct_length]      
            field_ends_at = enumerate(self.field_ends_at)
            field_num = [ i for i, j in field_ends_at if j > record_len ]
            sys.stderr.write('Field #%d truncated.\n' % field_num)
            mesg = 'No record data for field #%d.\n'
            if field_num == len(self.field_lengths):
                sys.stderr.write(mesg % field_num)
            else:
                mesg = mesg[:-6] + 's #%d-%d.\n' 
                sys.stderr.write(mesg % (field_num, self.num_fields))
            field_lengths[field_num - 1] = field_size_sum - record_length
            return field_lengths[:field_num], record
          
    def remove_filler(self, record_num, record):
        pass

   
def main(args):
    fields = load.csv_(args.copybook, strip_="right", prune=True)
    datetime_output_fmt = FormatDateTimeOutput(
        date_fmt = '%Y-%m-%d', time_fmt = '%H:%M:%S.%f')
    data = Data(fields, args, datetime_output_fmt)
    record = True
    record_num = 1
    while record:
        line = args.datafile.readline()
        if args.debug and line:
            sys.stdout.write('%s\n' % DBL_HORIZ_LINE)
            sys.stdout.write('RECORD NUMBER: %d\n' % record_num)
            sys.stdout.write('%s%s%s' % (HORIZ_LINE, line, HORIZ_LINE))
        record = data.parse_record(record_num, line, args.debug)
        if record:
            print record
        record_num += 1      

if __name__ == '__main__':
    from cmd_line_args import Args
    args = Args(USAGE, __version__)
    args.allow_stdin()
    args.add_files('copybook', 'datafile')
    args.add_options('debug')
    main(args.parse())
