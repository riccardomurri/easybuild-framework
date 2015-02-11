# #
# Copyright 2009-2014 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
# #
"""
EasyBuild logger and log utilities, including our own EasybuildError class.

@author: Stijn De Weirdt (Ghent University)
@author: Dries Verdegem (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Pieter De Baets (Ghent University)
@author: Jens Timmerman (Ghent University)
"""
import logging
import os
import sys
import tempfile
from copy import copy
from vsc.utils import fancylogger

from easybuild.tools.version import VERSION


# EasyBuild message prefix
EB_MSG_PREFIX = "=="

# the version seen by log.deprecated
CURRENT_VERSION = VERSION

# allow some experimental experimental code
EXPERIMENTAL = False

DEPRECATED_DOC_URL = 'http://easybuild.readthedocs.org/en/latest/Deprecated-functionality.html'


class EasyBuildError(Exception):
    """
    EasyBuildError is thrown when EasyBuild runs into something horribly wrong.
    """
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class EasyBuildLog(fancylogger.FancyLogger):
    """
    The EasyBuild logger, with its own error and exception functions.
    """

    # self.raiseError can be set to False disable raising the exception which is
    # necessary because logging.Logger.exception calls self.error
    raiseError = True

    def caller_info(self):
        """Return string with caller info."""
        (filepath, line, function_name) = self.findCaller()
        filepath_dirs = filepath.split(os.path.sep)

        for dirName in copy(filepath_dirs):
            if dirName != "easybuild":
                filepath_dirs.remove(dirName)
            else:
                break
            if not filepath_dirs:
                filepath_dirs = ['?']
        return "(at %s:%s in %s)" % (os.path.join(*filepath_dirs), line, function_name)

    def experimental(self, msg, *args, **kwargs):
        """Handle experimental functionality if EXPERIMENTAL is True, otherwise log error"""
        if EXPERIMENTAL:
            msg = 'Experimental functionality. Behaviour might change/be removed later. ' + msg
            self.warning(msg, *args, **kwargs)
        else:
            msg = 'Experimental functionality. Behaviour might change/be removed later (use --experimental option to enable). ' + msg
            self.error(msg, *args)

    def deprecated(self, msg, max_ver):
        """Print deprecation warning or raise an EasyBuildError, depending on max version allowed."""
        msg += "; see %s for more information" % DEPRECATED_DOC_URL
        fancylogger.FancyLogger.deprecated(self, msg, str(CURRENT_VERSION), max_ver, exception=EasyBuildError)

    def error(self, msg, *args, **kwargs):
        """Print error message and raise an EasyBuildError."""
        newMsg = "EasyBuild crashed with an error %s: %s" % (self.caller_info(), msg)
        fancylogger.FancyLogger.error(self, newMsg, *args, **kwargs)
        if self.raiseError:
            raise EasyBuildError(newMsg)

    def exception(self, msg, *args):
        """Print exception message and raise EasyBuildError."""
        # don't raise the exception from within error
        newMsg = "EasyBuild encountered an exception %s: %s" % (self.caller_info(), msg)

        self.raiseError = False
        fancylogger.FancyLogger.exception(self, newMsg, *args)
        self.raiseError = True

        raise EasyBuildError(newMsg)


class LoggerFactory(object):
    """
    Instanciate different logger classes, depending upon requested
    logger name.

    Loggers can be associated with prefixes; when a logger is
    requested, the constructor associated with the longest matching
    prefix is used to actually create the class instance.
    """

    def __init__(self, loggers):
        self._dispatch = {}
        self.dispatch('', logging.getLoggerClass())
        for prefix, cls in loggers.items():
            self.dispatch(prefix, cls)

    def dispatch(self, prefix, cls):
        """
        Register a logger of class `cls` to be used whenever a name
        starting with `prefix` is requested.
        """
        self._dispatch[prefix] = cls

    def __call__(self, name):
        """
        Create a logger with the specified name.

        The actual logger constructor is selected among the registered
        ones: the constructor associated with the longest matching
        prefix is used.
        """
        #sys.stderr.write("=== Requested logger for %s\n" % name)
        matched = -1
        logger = None
        for prefix, ctor in self._dispatch.items():
            if name.startswith(prefix) and len(prefix) > matched:
                matched = len(prefix)
                logger = ctor
        return logger(name)


# set format for logger
LOGGING_FORMAT = EB_MSG_PREFIX + ' %(asctime)s %(name)s %(levelname)s %(message)s'
fancylogger.setLogFormat(LOGGING_FORMAT)

# set the default LoggerClass depending on the caller
logDispatcher = LoggerFactory({
    # Ideally, one would use EasyBuildLog for EB and Python's default
    # for anything else, but the `easybuild.` prefix is stripped out
    # e.g. when one runs tests directly, but some EB code bombs out
    # when using Python's default Logger (not thread safe?).  Using
    # `FancyLogger` seems an acceptable compromise, in that it works
    # with both EB code and GC3Pie code...
    'easybuild': EasyBuildLog,
    '':          fancylogger.FancyLogger,
    #'':          logging.Logger,
})
# `logging.setLoggerClass` insists that the passed callable is a class
# definition and that it derives from `logging.Logger` (or the current
# Logger); I cannot see a way of adapting the log dispatcher to meet
# those requirements, so let us just bypass `logging.setLoggerClass`
# and set the logger class by accessing a private global variable
# directly.  Not kosher, but it works.
logging._loggerClass = logDispatcher

# you can't easily set another LoggerClass before fancylogger calls getLogger on import
_init_fancylog = fancylogger.getLogger(fname=False)
del _init_fancylog.manager.loggerDict[_init_fancylog.name]

# we need to make sure there is a handler
fancylogger.logToFile(filename=os.devnull)

# EasyBuildLog
_init_easybuildlog = fancylogger.getLogger(fname=False)


def init_logging(logfile, logtostdout=False, testing=False):
    """Initialize logging."""
    if logtostdout:
        fancylogger.logToScreen(enable=True, stdout=True)
    else:
        if logfile is None:
            # mkstemp returns (fd,filename), fd is from os.open, not regular open!
            fd, logfile = tempfile.mkstemp(suffix='.log', prefix='easybuild-')
            os.close(fd)

        fancylogger.logToFile(logfile)
        print_msg('temporary log file in case of crash %s' % (logfile), log=None, silent=testing)

    log = fancylogger.getLogger(fname=False)

    return log, logfile


def stop_logging(logfile, logtostdout=False):
    """Stop logging."""
    if logtostdout:
        fancylogger.logToScreen(enable=False, stdout=True)
    fancylogger.logToFile(logfile, enable=False)


def get_log(name=None):
    """
    Generate logger object
    """
    # fname is always get_log, useless
    log = fancylogger.getLogger(name, fname=False)
    log.info("Logger started for %s." % name)
    log.deprecated("get_log", "2.0")
    return log


def print_msg(msg, log=None, silent=False, prefix=True):
    """
    Print a message to stdout.
    """
    if log:
        log.info(msg)
    if not silent:
        if prefix:
            print "%s %s" % (EB_MSG_PREFIX, msg)
        else:
            print msg


def print_error(message, log=None, exitCode=1, opt_parser=None, exit_on_error=True, silent=False):
    """
    Print error message and exit EasyBuild
    """
    if exit_on_error:
        if not silent:
            if opt_parser:
                opt_parser.print_shorthelp()
            sys.stderr.write("ERROR: %s\n" % message)
        sys.exit(exitCode)
    elif log is not None:
        log.error(message)


def print_warning(message, silent=False):
    """
    Print warning message.
    """
    print_msg("WARNING: %s\n" % message, silent=silent)
