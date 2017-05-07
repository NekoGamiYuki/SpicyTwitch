# Imports-----------------------------------------------------------------------
import os
from time import time
from inspect import stack, getmodulename  # Maybe cause compatibility issues
from ... import irc, log_tools, storage
from . import module_classes

# Global Variables--------------------------------------------------------------
# Defaults
DEFAULT_EVERYONE_COOLDOWN = 30
DEFAULT_MOD_COOLDOWN = 5
DEFAULT_COMMAND_PREFIX = '!'

USER_LEVELS = [
    "moderator", "broadcaster", "subscriber", "everyone"
]

# Logging
_logger = log_tools.create_logger()

# Data Dictionaries
RESPONSE_MODULES = {}
MODERATION_MODULES = {}
TIMERS = {}

# Reservations
RESERVED_COMMANDS = []

SHUTDOWN_FUNCTIONS = []

# Storage setup-----------------------------------------------------------------
main_storage = os.path.join(storage.primary_storage_directory, 'modules')

if not os.path.exists(main_storage):
    os.mkdir(main_storage)

# General functions-------------------------------------------------------------
# Command related---
def default_check_user_level(level: str, user: irc.User) -> bool:
    """Compares irc.User to the given (and known) userlevel

    The known userlevels are in the module.tools.USER_LEVELS list.

    :param level: Level that will be compared with the User's level.
    :param user: The irc.User object.
    :return: True if levels match, else it returns False
    """
    if level == "moderator":
        # So that the channel owner may also use moderator commands.
        return user.is_mod or user.is_broadcaster
    elif level == "broadcaster":
        return user.is_broadcaster
    elif level == "subscriber":
        return user.is_sub
    elif level == "everyone":
        return True
    else:
        return False


def get_storage_directory():
    all_modules = (RESPONSE_MODULES, MODERATION_MODULES)
    module_name = get_module_name()

    for category in all_modules:
        try:
            directory = category[module_name].storage_directory
            
            if not os.path.exists(directory):
                os.mkdir(directory)

            return directory
        except KeyError:
            continue
    else:  # Yes, I know it's strange but python allows this!
        raise RuntimeError(
            "Unregistered module requested a storage directory. Please register "
            "your module before interacting with the rest of the tools."
        )



# Inspection--------------------------------------------------------------------
def get_module_name() -> str:
    """Gets the name of the module that called a function

    Is meant to be used within a function.

    :returns: The name of the module that called your function
    """
    return getmodulename(stack()[2][1])


# Commands related--------------------------------------------------------------
def check_if_command_exists(command_name: str, ignore_casing: bool=False) -> bool:

    if command_name.lower() in RESERVED_COMMANDS:
        return True

    for name, module in RESPONSE_MODULES.items():
        if module.check_if_command_exists(command_name, ignore_casing):
            return True
        else:
            continue

    return False


def reserve_general_commands(commands: list):
    """Reserves a command name

    In cases where a command is more complex than a single word, such as when
    using regex, the base command will not be reserved and other modules may
    end up registering a command that conflicts with others. 

    For example, here is a command for getting the uptime of a stream:
        REGEX: r'uptime( [\w\W]+)?'
        ALONE: 'uptime'

    To a user both look the same, with the exception that one can take extra
    input, but to the system these are both different as I have yet to find a
    way to extract the base command (the 'uptime') from regex. For that reason,
    this function can help to reduce or even eliminate such conflicts.

    :param commands: A list of commands (strings) that will be reserved
    """

    global RESERVED_COMMANDS

    module = get_module_name()
    for command in commands:
        # Make sure we get a string
        if isinstance(command, str):
            if command.lower() not in RESERVED_COMMANDS:
                _logger.info("Reserving command: '{}'".format(command.lower()))
                # Add command to reserved commands list
                RESERVED_COMMANDS.append(command.lower())
            else:
                # NOTE: Raise so as to not have a programmer assume that their
                #       command was reserved by them and ONLY them.
                raise RuntimeError(
                    "Module '{}' attempted to reserve a name that was already "
                    "reserved beforehand. Command: {}".format(module, command)
                )
        else:
            raise RuntimeError(
                "Reserved commands list should only contain strings."
            )


def register_command_module():
    """Registeres a command module so that it may then register commands

    """
    global RESPONSE_MODULES

    module_name = get_module_name()
    if module_name in RESPONSE_MODULES:
        raise RuntimeError(
            "Module '{}' is already registered. Please make sure to not register "
            "more than once. Another thing to look out for is if another module "
            "has the same name as the one currently registering."
        )

    _logger.info("Registering Command Module: {}".format(module_name))
    RESPONSE_MODULES[module_name] = module_classes.CommandModule(
        module_name, DEFAULT_COMMAND_PREFIX, os.path.join(main_storage, module_name)
    )


def register_command(
    name: str,
    command_function: callable,
    user_level: str='everyone',
    everyone_cooldown: int=DEFAULT_EVERYONE_COOLDOWN,
    mod_cooldown: int=DEFAULT_MOD_COOLDOWN,
    valid_user_levels: list=USER_LEVELS,
    user_level_validator: callable=default_check_user_level,
    ignore_casing: bool=False
):
    """Adds a command to the system, allowing it to be used in Twitch

    Adds the command to the module's class in the RESPONSE_MODULES dict.

    :param name:
        The name of the command, used in twitch, can be regex.
    :param command_function: 
        The function that will be called when the command is ran.
    :param user_level: 
        The user level necessary to be able to run the command
    :param everyone_cooldown:
        The base cooldown that affects general viewers.
    :param mod_cooldown:
        The cooldown that affects moderators. This also affects the broadcaster.
        (A decision made to disallow a hacked broadcaster from being able to 
        spam commands)
    :param valid_user_levels: 
        A list of valid user levels. This is used when changing the user level 
        of the command.
    :param user_level_validator:
        A function that will assist in validating the level of a user. Takes in 
        two arguments, a string and an irc.User object.
    :param ignore_casing: 
        Whether or not to ignore casing for the command. If enabled, commands such
        as 'uptime' and 'UPTIME' will be counted as the same command. Off by default
        so as to not affect regex.
    """
    global RESPONSE_MODULES
    
    # Make sure name is not blank
    if not name:
        raise RuntimeError("Command name must not be blank string")

    # Make sure user level was given when using default validator and valid levels
    if not user_level and valid_user_levels == USER_LEVELS\
    and user_level_validator == default_check_user_level:
        raise RuntimeError(
            "User level must not be blank when using the default command settings"
        )

    # Make sure a user level validator was given if the valid user levels was changed
    if valid_user_levels != USER_LEVELS and user_level_validator != default_check_user_level:
        raise RuntimeError(
            "You must provide a user level validator function if you change the default "
            "valid user levels! If this is not done the command will never execute."
        )

    # Make sure user level is in valid user levels list.
    if user_level not in valid_user_levels:
        raise RuntimeError(
            "User level is invalid. Please make sure user_level is in the list of "
            "valid user levels. Invalid Level: {}".format(user_level)
        )


    if everyone_cooldown < 0 or mod_cooldown < 0:
        raise RuntimeError(
            "Cooldown must not be negative"
        )

    module_name = get_module_name()
    if everyone_cooldown < 5 or mod_cooldown < 5:
        _logger.warning(
            "A Cooldown for command '{}' in module '{}' is less than 5 seconds! This could "
            "result in the bot getting banned! Be careful!".format(name, module_name)
        )
    
    # If all checks out, add the new command
    try:
        RESPONSE_MODULES[module_name].add_command(
            module_classes.Command(
                name,
                command_function,
                user_level,
                everyone_cooldown,
                mod_cooldown,
                valid_user_levels,
                user_level_validator,
                ignore_casing
            )
        )
        _logger.info("Registering command '{}' for module '{}'.".format(name, module_name))
    except KeyError:
        raise RuntimeError(
            "Module '{}' attempted to register a command without having previously "
            "registered as a command module!".format(module_name)
        )

# Shutdown functions------------------------------------------------------------
def register_shutdown_function(function: callable):
    all_modules = (RESPONSE_MODULES, MODERATION_MODULES)
    module_name = get_module_name()

    for category in all_modules:
        try:
            temp = category[module_name].name
            break
        except KeyError:
            continue
    else:
        raise RuntimeError(
            "Module '{}' attempted to register a shutdown function without "
            "having previously registered their module. Please register your "
            "module before using the rest of the tools!".format(module_name)
        )

    global SHUTDOWN_FUNCTIONS
    if function not in SHUTDOWN_FUNCTIONS:
        SHUTDOWN_FUNCTIONS.append(function)
