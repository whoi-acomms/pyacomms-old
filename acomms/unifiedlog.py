__author__ = 'Eric'

import logging
import time
import os
from datetime import datetime


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

