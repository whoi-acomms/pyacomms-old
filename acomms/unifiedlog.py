__author__ = 'Eric'

import logging
import os
import time
from datetime import datetime


class UnifiedLog(object):
    def __init__(self, log_path=None, file_name=None, console_log_level=None, rootname=None, custom_handler=None):

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

        if custom_handler is not None:
            self._log.addHandler(custom_handler)

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

        self.log_file_name = log_file_path

        self._file_handler = logging.FileHandler(log_file_path)
        self._file_handler.setLevel(logging.DEBUG)
        self._file_handler.setFormatter(self._logformat)
        self._log.addHandler(self._file_handler)

    def log_file_path(self): #Added to try and help error in downlinktest_all.py -Dana
        return self.log_file_name

    def getLogger(self, name):
        return self._log.getChild(name)

    def start_django_output(self, model, test_script_run):
        self._django_handler = DjangoHandler(model, test_script_run)
        self._log.addHandler(self._django_handler)


class DjangoHandler(logging.Handler):
    def __init__(self, model=None, test_script_run=None):
        super(DjangoHandler,self).__init__()
        self.model = model
        self.test_script_run = test_script_run

    def emit(self, record):
        ts = datetime.utcfromtimestamp(record.created)
        entry = self.model(test_script_run=self.test_script_run, timestamp=ts, level=record.levelname, name=record.name, message=record.message)
        entry.save()
