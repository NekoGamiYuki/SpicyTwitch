"""
This module will manage two main parts of the system.

First:
It will manage configuration of every other command module
"""
# Imports---------------------------------------------------------------------
import re
from .. import irc

# Regex-----------------------------------------------------------------------
# TODO: I believe I need to do a check at the start of each regex.
#       I'll check for a character as that's what'll be used to denote a call.
add_regex = re.compile(r"commands add (--\w+=\w+)? (\w+) (\w+|\W+)")
edit_regex = re.compile(r"commands edit (--\w+=\w+)? (\w+) (\w+|\W+)")
delete_regex = re.compile(r"commands (delete|remove) (\w+)")
rename_regex = re.compile(r"commands rename (\w+)")
config_regex = re.compile(r"config edit (\w+) (\w+) (\w+)")

