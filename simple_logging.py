"""
Author: NekoGamiYuki
Version: 0.0.0

Description:
A rather simple logging API. Created for use in my Twitch API.
"""

# TODO: Consider turning this entire module into a single class!
# TODO: Update all print statements to use .format instead of %
# This way, multiple log files chan be created1

import os
import inspect  # Should consider not using this... (Not good in other interps)
from datetime import datetime

# Logging! (DO NOT set these yourself, use turn_on()/turn_off() instead)
log_is_on = False
_LOGFILE_NAME = ""


# Logging-----------------------------------------------------------------------
def log_verbose(info='', caller_function=''):
    """
    Prints out a log to the console. Automatically gets the name of the function
    that called it. In case it is unable to, log_verbose() will use the place-
    holder "COULD NOT FIND FUNCTION NAME". If this is a constant issue, the
    caller_function parameter can be used to manually set the function name.

    Args:
        info: What will be printed out to the console
        caller_function: Name of the function that is printing a log

    Returns:
        True: Whenever it prints out to the console
        False: If it is unable to print out or is given no information to print

    """

    # Get the name of the function that called us
    if caller_function:
        function_name = caller_function
    else:
        if not inspect.stack():
            function_name = "COULD NOT FIND FUNCTION NAME"
        else:
            function_name = inspect.stack()[1].function

    if info:
        try:
            print("[{}] {}(): {}".format(datetime.now(),
                                         function_name,
                                         info.strip()))
            return True
        except IOError:
            return False
    else:
        log_verbose("log_verbose(): Was ran but "
                    "given no information to print!")
        return False


def turn_on(log_file="default_log_file.log",
            message="Beginning log...",
            verbose_output=False):
    """
    Turns on logging. By default it writes to the file "default_log_file.log"
    and starts off by writing "Beginning log...". Both the log file and message
    can be set in parameters.

    Args:
        log_file: The log file you'd like to write to
        message: The first message written to the log file (An entrance!)
        verbose_output: Have turn_on() tell you what it is doing

    Returns:
        False: When it isn't able to turn on logging (or it's already on)
        True: When it turns on logging

    """

    global _LOGFILE_NAME
    global log_is_on

    # Check if logging is already on
    if log_is_on:
        if verbose_output:
            log_verbose("Logging is already on")

        log_write("Logging is already on")
        return False

    # Create log file if one isn't existent
    if not os.path.isfile(log_file):
        try:
            if verbose_output:
                log_verbose("No log file found. Creating log file.")

            with open(log_file, "a+") as _LOGFILE:
                _LOGFILE.write("[%s] turn_on(): Log file created! "
                               "Let the debugging begin! "
                               "(The log file is not updated in real time, "
                               "instead it is updated when the program/api "
                               "closes)\n" % datetime.now())
                _LOGFILE.write("[%s] turn_on(): %s\n"
                               % (datetime.now(), message))

            if verbose_output:
                log_verbose("Log file has been created!")

            _LOGFILE_NAME = log_file
            log_is_on = True

            if verbose_output:
                log_verbose("Logging is now on!")
            return True
        except IOError:
            log_verbose("Unable to create log file."
                        "logging will be turned off. Is the disk full?")
            log_is_on = False
            return False
    else:
        try:
            with open(log_file, "a+") as _LOGFILE:
                _LOGFILE.write("-" * 80 + '\n')
                _LOGFILE.write("[%s] turn_on(): %s\n"
                               % (datetime.now(), message))
                _LOGFILE.close()

            log_is_on = True
            _LOGFILE_NAME = log_file

            if verbose_output:
                log_verbose("Logging is now on!")
        except IOError:
            log_verbose("Unable to write to the  log file."
                        "logging will be turned off. Is the disk full? Are"
                        "permissions not set correctly?")
            log_is_on = False
            return False


def log_write(info='', caller_function='', verbose_output=True):
    """
    Writes to the log file. Checks to make sure the log file still exists, as
    well as checking if it hasn't suddenly been cleared out and lost all info.
    If it is unable to find the log file, it will attempt to create a new one
    by re-calling turn_on() with a message explaining what happened. In the end,
    if log_write is simply incapable of writing to the log file (whether that be
    because it couldn't create a new file, permission issues, or was given an
    empty string) log_write will return False. Else, if it is able to write a
    log, it will return True.

    Args:
        info: What you would like to have written to the log file
        caller_function: The name of the function that is calling log_write()
        verbose_output: Have the function print out what it is doing.

    Returns:
        True: If it is able to write to the log file
        False: When it isn't able to write to the log file.
    """

    global log_is_on

    if "replacement" in _LOGFILE_NAME:
        empty_file_message = ('WARNING!!! Wrote to replacement file with no '
                              "previous data. Did someone clear the log file?")
    else:
        empty_file_message = ('WARNING!!! Wrote to log file with no previous '
                              "data. Did someone clear the log file?")

    # Get the name of the function that called us
    if caller_function:
        function_name = caller_function
    else:
        if not inspect.stack():
            function_name = "COULD NOT FIND FUNCTION NAME"
        else:
            function_name = inspect.stack()[1].function

    # Check if the log file exists (No point in writing to an inexistent file)
    if not os.path.isfile(_LOGFILE_NAME):
        if verbose_output:
            log_verbose("Log file is missing! Did someone delete it!?")

        if verbose_output:
            log_verbose("Attempting to create a replacement "
                        "log file using turn_on()")

        previous_filename = _LOGFILE_NAME.split('.')[0]
        extension = _LOGFILE_NAME.split('.')[1]

        if verbose_output:
            log_verbose("Temporarily turning off logging to create "
                        "replacement log file.")

        log_is_on = False

        if not extension:
            extension = "log"

        if not turn_on("{}_replacement.{}".format(previous_filename, extension),
                       "WARNING!!! The log file was missing! This file was "
                       "created as a replacement. Did someone mess with the "
                       "original!?", verbose_output):
            log_verbose("Log file could not be created. Logging is now "
                        "turned off.")
            log_is_on = False
            return False
        else:
            if verbose_output:
                log_verbose("Log file created. Continuing with logging!")

    if log_is_on:
        try:
            # Check if the file is empty (It should not be...)
            if not os.stat(_LOGFILE_NAME).st_size:
                if verbose_output:
                    log_verbose(empty_file_message)

                with open(_LOGFILE_NAME, 'a+') as _LOGFILE:
                    _LOGFILE.write("[{}] log_write(): {}\n".format(
                        datetime.now(), empty_file_message))

            # Check if we were given info to log
            if not info:
                if verbose_output:
                    log_verbose("Was called for logging but"
                                " given no information to log.")
                return False
            else:
                with open(_LOGFILE_NAME, 'a+') as _LOGFILE:
                    _LOGFILE.write("[{}] {}(): {}\n".format(datetime.now(),
                                                            function_name,
                                                            info.strip()))
                return True

        except OSError:
            if verbose_output:
                log_verbose("Unable to write to log!"
                            "(Have permissions changed for the file?)")
            return False
    else:
        if verbose_output:
            log_verbose("Unable to write log (Logging is turned off!)")
        return False


def turn_off(verbose_output=False, message="Logging has been turned off."):
    """
    Used to turn off logging.

    Args:
        verbose_output: Have the function print out what it is doing
        message: If you'd like, change what it says when it finishes running.

    Returns:
        True: If it is able to turn off logging
        False: If the function is ran when logging is off.
    """

    global log_is_on

    if log_is_on and _LOGFILE_NAME:
        log_is_on = False
        if verbose_output:
            log_verbose(message)
        return True
    else:
        if verbose_output:
            log_verbose("Logging is not on. (Nothing to turn off)")
        return False
