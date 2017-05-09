# Imports-----------------------------------------------------------------------
import logging
import os
from inspect import stack, getmodulename
from . import storage


# Base setup--------------------------------------------------------------------
log_to_stdout = True
log_to_file = True
logging_level = logging.INFO
log_format = '[%(asctime)s] [%(levelname)s] [%(module)s] (%(funcName)s): ' \
             '%(message)s'
date_format = '%Y/%m/%d %I:%M:%S %p'
log_formatter = logging.Formatter(log_format, datefmt=date_format)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

log_storage = os.path.join(storage.primary_storage_directory, 'logs')

if not os.path.exists(log_storage):
    os.mkdir(log_storage)

# Functions---------------------------------------------------------------------
def get_module_name() -> str:
    """Gets the name of the module that called a function

    Is meant to be used within a function.

    :returns: The name of the module that called your function
    """
    return getmodulename(stack()[2][1])


def create_logger(allow_file_logging: bool=True) -> logging.Logger:
    python_module = get_module_name()

    module_logger = logging.getLogger(python_module)

    if log_to_stdout:
        module_logger.addHandler(console_handler)

    if log_to_file and allow_file_logging:
        file_path = os.path.join(log_storage, python_module + '.log')
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(log_formatter)
        module_logger.addHandler(file_handler)

    module_logger.setLevel(logging_level)
    return module_logger
