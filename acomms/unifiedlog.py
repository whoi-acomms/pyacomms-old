__author__ = 'Eric'

import logging
import os
import time
from datetime import datetime
try:
    import sqlite3
except ImportError:
    pass


class UnifiedLog(object):
    def __init__(self, log_path=None, file_name=None, console_log_level=None, rootname=None):

        # Create the logger
        if rootname is not None:
            self._log = logging.getLogger(rootname)
        else:
            self._log = logging.getLogger()

        # Use UTC timestamps in ISO8601 format
        self._logformat = logging.Formatter("%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s", "%Y-%m-%dT%H:%M:%SZ")
        self._logformat.converter = time.gmtime

        if console_log_level is not None:
            self._console_handler = logging.StreamHandler()
            self._console_handler.setLevel(console_log_level)
            self._console_handler.setFormatter(self._logformat)
            self._log.addHandler(self._console_handler)

        # If no log path is specified, use (or create) a directory in the user's home directory
        if log_path is None:
            log_path = os.path.expanduser('~/acomms_logs')

        log_path = os.path.normpath(log_path)

        # Create the directory if it doesn't exist
        if not os.path.isdir(log_path):
            os.makedirs(log_path)

        if file_name is None:
            now = datetime.utcnow()
            file_name = "acomms_{0}.log".format(now.strftime("%Y%m%dT%H%M%SZ"))

        log_file_path = os.path.join(log_path, file_name)

        self._file_handler = logging.FileHandler(log_file_path)
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(self._logformat)
        self._log.addHandler(self._file_handler)

    def getLogger(self, name):
        return self._log.getChild(name)


    def start_html_output(self):
        self._html_format = logging.Formatter("<tr><td>%(asctime)s</td><td>%(levelname)s</td><td>%(name)s</td><td>%(message)s</td></tr>", "%Y-%m-%dT%H:%M:%SZ")
        self._html_format.converter = time.gmtime

        log_path = os.path.expanduser('~/acomms_logs/html.tmp')

        self._html_handler = logging.FileHandler(log_path, mode='w')
        self._html_handler.setFormatter(self._html_format)
        self._log.addHandler(self._html_handler)

    def start_django_output(self, model, test_script_run):
        self._django_handler = DjangoHandler(model, test_script_run)
        self._log.addHandler(self._django_handler)

'''
class SQLiteHandler(logging.Handler): # Inherit from logging.Handler
    def __init__(self, filename):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Our custom argument
        self.db = sqlite3.connect(filename) # might need to use self.filename
        self.db.execute("CREATE TABLE IF NOT EXISTS log(timestamp text, level text, name text, message text)")
        self.db.commit()

    def emit(self, record):
        # record.message is the log message
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created))
        sqlcmd = "INSERT INTO log(timestamp, level, name, message) VALUES('{ts}','{level}','{name}','{message}')".format(
                ts=ts, level=record.levelname, name=record.name, message=record.message)
        self.db.execute(sqlcmd)
        self.db.commit()
'''


class DjangoHandler(logging.Handler):
    def __init__(self, model=None, test_script_run=None):
        super(DjangoHandler,self).__init__()
        self.model = model
        self.test_script_run = test_script_run

    def emit(self, record):
        ts = datetime.utcfromtimestamp(record.created)
        entry = self.model(test_script_run=self.test_script_run, timestamp=ts, level=record.levelname, name=record.name, message=record.message)
        entry.save()
