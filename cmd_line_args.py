import argparse, sys

__all__ = ['Args']

class VersionAction(argparse.Action):
    """Overrides argparse_VersionAction(Action) to allow line feeds within
    version display information.""" 
    def __init__(self, option_strings, version=None, 
         dest=None, default=None, help=None):
         super(VersionAction, self).__init__(option_strings=option_strings,
             dest=dest, default=default, nargs=0, help=help)
         self.version = version

    def __call__(self, parser, namespace, values, option_string=None):
        version = self.version
        if version is None:
            version = parser.version
        print version
        parser.exit()

class Args:
    """argparse wrapper"""
    
    allow_stdin = False
    
    def __init__(self, usage, version):
        self.parser = argparse.ArgumentParser(usage=usage)
        self.parser.version = version
        self.parser.add_argument('-V', '--version', 
            action = VersionAction,
            help='display version information and exit')
    
    def add_files(self, *file_args):
        """Add positional filename argurments.  If self.allow_stdin is set
        Example:
            object.add_filenames('config_file', 'data_file'])
            The 1st filename will be saved in a variable called 'config_file'.
            The 2st filename will be saved in a variable called 'data_file'.
        """
        if self.allow_stdin:
            for file_arg in file_args[:-1]:
                self.parser.add_argument(file_arg, help='filename... %s' % file_arg)
            self.parser.add_argument(file_args[-1], 
                help='filename... %s' % file_args[-1], nargs='?')
        else:
            for file_arg in file_args:
                self.parser.add_argument(file_arg, help='filename... %s' % file_arg)      
        self.file_args = file_args
  
    def add_filelist(self):
        """FUTURE: ability to add a list of files to be processed.  Similar to
        python filelist module, but with ability to include other arguments.
        Support for wildcards."""
        pass
        
    def add_options(self, *options):
        """Add from a standard library of pre-defined command-line arguments"""
        for option in options:
            option = option.lower()
            if option == 'debug':
                self.parser.add_argument('-d', '--debug', action='store_true',
                    help='Turn on debug mode.')
            elif option == 'debug_level':
                self.parser.add_argument('-d', '--debug', type=int,
                    help='Set debug level 1-10.')
            elif option == 'verbose':
                self.parser.add_argument('-v', '--verbose', action='store_true',
                    help='Turn on verbose mode.')
            elif option == 'quiet':
                self.parser.add_argument('-q', '--quiet', action='store_true',
                    help='Suppress all output to terminal.')
    
    def allow_stdin(self):
        self.allow_stdin = True

    def parse(self):
        """Parse args & use sys.stdin if applicable
        Sets all file arguments to a file read object"""
        args = self.parser.parse_args()
        if hasattr(self, 'file_args'):
            if self.allow_stdin:
                if not sys.stdin.isatty():
                    setattr(args, self.file_args[-1], sys.stdin)
                else:
                    self.allow_stdin = False
            last_arg_idx = len(self.file_args) - self.allow_stdin
            for file_arg in self.file_args[:last_arg_idx]:
                try:
                    file_ = open(getattr(args, file_arg))
                except IOError, error_msg:
                    sys.stderr.write('ERROR loading file "%s".\n%s\n' % 
                        (file_arg, error_msg))
                    sys.exit(1)
                setattr(args, file_arg, file_)        
        return args
    