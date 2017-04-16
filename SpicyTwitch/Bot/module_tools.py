"""
Author: NekoGamiYuki
Version: 1.0.1

!!! WARNING !!!
I really think I need to go through this and just rewrite it all. It feels as if
I am doing some very inefficient things, the system could be better. So please,
if you want to use this just know that things will likely change, you may also
run into some performance issues.

Description:
A set of tools to help command modules work more efficiently in combination with
the rest of the command system that SpicyTwitch has.
"""
# TODO: With datbase implementation, only modules can be disabled and not
#       specific features within the module. Maybe I should let modules handle
#       whether or not they'll run for specific channels?
# TODO: Go through functions and assign variables to lower() version before
#       usage, rather than constantly calling var.lower().
#
#       Like this: var = var.lower()
#
# TODO: Work on timers. As I'm having a few issues with the system.
#       - Maybe I could just make a very simple system where the timer
#         manager just runs a command ?
# TODO: Add timer functionality
# TODO: Add docstrings to all functions
# TODO: Read up on properly using python, some of the things I've done feel like
#       there may be better ways to do them.
# NOTE: I think if I use function decorators I can do some fun stuff, like maybe
#       that would be an easier thing to do than having users register their
#       commands?
# NOTE: When I learn more, I think I might be able to create decorators for each
#       command type (response/one-way/timer) and also make it so that if a
#       module isn't registered, it'll be auto-registered on command
#       registration.
# TODO: Add register_filter() for Moderation modules to use.
#       The can still use register_command() if they'd like to have some
#       commands, such as ones that can show how many people have been timed out
#       by a link filter.
# TODO: Also add register_timer() for Timer modules to use.
# TODO: Also add register_oneway() for One-Way modules to use.
# TODO: Add ability to make users "managers" for a channel.
#       I should just turn this idea into an "Administration" module
# TODO: Log certain exceptions by converting them to str().
# TODO: Going to have to create a check that the basic keys are loaded correctly
#       Specifically, things like 'data', which are critical for use in many
#       commands. Since these are loaded first, if available, there's a chance
#       that something may happen where a file is deleted and that would break
#       the rest of the system.
# TODO: Consider how much power the broadcaster should have.
#       I've been wondering if the broadcaster should be exempt from things like
#       cooldowns. On one hand, they get as much power as possible over the bot
#       and are able to instantly have access to any commands they need. On the
#       other hand, if they're ever hacked then a lot of damage can be done with
#       that instant access. A cooldown could limit how much can be done by
#       giving a streamer time to react and, if possible, get their account back
#       before a significant amount of damage is done (like deleting all
#       commands). The cooldown would be small though, which means there
#       wouldn't be much time, but SOME time is better than no time right?
# TODO: Make an emote list that modules can use.
#       These would be used for responses, allowing a bot to instantly change
#       the emotes it is uses for any module that uses them.
#
#       I'll have a function for updating the emote dictionary so that I can
#       save and load the emotes into a database. Users will be able to just
#       do 'module_tools.emotes["Greetings"]'. 
#
#       Example:
#       Greetings: HeyGuys
#       Content: SeemsGood
#       Happy: FeelsGoodMan
#       VeryHappy: FeelsAmazingMan
#       Sad: FeelsBadMan
#       Crying: BibleThump
#       Joking/Sarcasm: Kappa
#       Excited: PogChamp
#       Cute: FeelCuteMan
#       Lewd: cirLewd
#       Facepalm: FailFish
#       Anime: VoHiYo
#       Shouting: SwiftRage
#       Partying: SourPls/(ditto)/dittoPride
#       Disgusted: DansGame
#       Thinking: sfhHM
#       Scared: WutFace
#       Perplexed: NotLikeThis
# TODO: Fix the name system for module tools
#       Currently it works just fine if the module does not input its own name.
#       If a module does, then certain features have not been updated to work
#       with name input. Also, maybe we should just tie the name to the module's
#       actual file name. However, I feel this could lead to name collisions.
# TODO: Create a logger for this module and log everything!
# NOTE: Bad news for the logger... it doesn't seem to be working...
#       As I'm creating the sacrifice module, I've noticed that I might have
#       some performance issues with modules that have to repeatedly request
#       and update their data. If this is an issue, I should consider placing
#       the data dictionary outside of the modules dictionary.
# NOTE: Managing data is becoming quite the issue and I'm thinking that I should
#       just let modules do what they want when it comes to saving data. Instead
#       it would be preferable if this module did only two things, logging and
#       executing module commands.
#           I'll just have a database with the following tables:
#               - general commands
#                   - command
#                   - response
#                   - channel
#                   - enabled
#                   - creation date
#                   - created by
#                   - edit date
#                   - edited by
#               - modules
#                   - name
#                   - commands
#                   - channels (where it is enabled)

# Imports-----------------------------------------------------------------------
import sqlite3
import time
import inspect  # May ruin compatibility with anything other than CPython!
import re
import logging
import warnings
import platform
import os
from .. import IRC


# Global Variables--------------------------------------------------------------
# Configuration
DEFAULT_COMMAND_PREFIX = '!'
USER_LEVELS = ["moderator", "broadcaster", "subscriber", "everyone"]
CATEGORIES = ["moderation", "response", "one-way", "timer"]
DEFAULT_COOLDOWN = 30
DEFAULT_MOD_COOLDOWN = 5
DEFAULT_USERLEVEL = "everyone"

# Logging
log_to_stdout = True
log_to_file = True
logging_level = logging.INFO
log_format = '[%(asctime)s] [%(levelname)s] [%(module)s] (%(funcName)s): ' \
             '%(message)s'
date_format = '%Y/%m/%d %I:%M:%S %p'
log_formatter = logging.Formatter(log_format, datefmt=date_format)

# Setting up the logger for this module
_logger = logging.getLogger(__name__)

# Setting up terminal/console output for loggers
if log_to_stdout:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    _logger.addHandler(console_handler)

# Modules and Systems
# Apparently no performance issues with having everything in one dictionary!
# Well, no issues as far as lookup time goes.
_MODULES = {}
_SHUTDOWN_FUNCTIONS = []  # Called on shutdown of bot.


# Storage Setup-----------------------------------------------------------------
# This sets up the storage directory based on the OS it is being run on.
# TODO: Add support for BSD, specifically FreeBSD.
os_name = platform.system()
if os_name == "Darwin" or os_name == "Windows":  # NOTE: Darwin is Mac OS
    primary_storage_directory = os.path.join(os.path.expanduser('~'),
                                             "Documents",
                                             "SpicyTwitch")
elif os_name == "Linux":  # I'd like to interject for a moment...
    primary_storage_directory = os.path.join(os.path.expanduser('~'),
                                             ".config",
                                             "spicytwitch")
else:
    # TODO: Consider placing storage in same directory as file and warning user.
    #       of storage issue?
    raise RuntimeError("Unsupported/Untested OS is being run.")

_logger.info(
    "Storage directory has been set to: {}".format(primary_storage_directory)
)

if not os.path.exists(primary_storage_directory):
    # Please don't come back to bite me in the butt...  os.makedirs()
    _logger.info(
        "Primary storage path did not exist, creating folders."
    )


log_directory = os.path.join(primary_storage_directory, "logs")
if log_to_file and not os.path.exists(log_directory):
    os.makedirs(log_directory)

    # Turning on logging to file for the module_tools logger
    _file_path = os.path.join(log_directory, "module_tools.log")
    _file_handler = logging.FileHandler(_file_path)
    _file_handler.setFormatter(log_formatter)
    _logger.addHandler(_file_handler)


# For modules to be able to know what their storage directory is.
def get_storage_directory() -> str:
    module_name = get_module_name()

    try:
        if module_name.lower() in _MODULES.keys():
            directory = _MODULES[module_name.lower()]["storage"]

            _logger.info(
                "Module {} requested storage. Returning directory: "
                "{}".format(module_name, directory)
            )
            return directory
        else:
            warnings.warn("Module name '{}' unrecognized. No storage "
                          "directory will be given.".format(module_name))
            return ''
    except KeyError:
        # TODO: LOG critical error with 'storage' missing from dictionary.
        return ''


# Database----------------------------------------------------------------------
_logger.info("Connecting to database")
DATABASE_FILE = "module_tools.db"
connection = sqlite3.connect(os.path.join(primary_storage_directory, DATABASE_FILE))
cursor = connection.cursor()


# Setting up module tables ---
# General commands
cursor.execute(
    "CREATE TABLE IF NOT EXISTS general_commands "
    "(response TEXT, name TEXT, usage INT, cooldown INT, last_call REAL, "
    "user_level TEXT created_by TEXT, channel TEXT, enabled TEXT)"
)

# Modules
cursor.execute(
    "CREATE TABLE IF NOT EXISTS modules "
    "(name TEXT, channels TEXT)"
)


# Inspection--------------------------------------------------------------------
def get_module_name(outer_module: bool=True) -> str:
    stack = inspect.stack()

    if outer_module:
        # With an index of two, we'll get the name of the module that called
        # this function, outside of this module.
        stack_index = 2
    else:
        # With an index of one, we'll get the latest module name, which in this
        # module will be module_tools.
        stack_index = 1

    return inspect.getmodulename(stack[stack_index][1])


# NOTE: Has not been tested!
def get_function_name(outer_module: bool=True) -> str:
    stack = inspect.stack()

    if outer_module:
        stack_index = 2
    else:
        stack_index = 1

    return stack[stack_index][3]


# Logging System----------------------------------------------------------------
def create_logger() -> logging.Logger:
    """Creates a logger with the module's name and adds it to a local dict.

    Creates a logger using the logging module, using getLogger() with the name
    given by the gen_module_name() function.

    :return: logging.Logger object
    """

    python_module_name = get_module_name()

    # Creating the logger
    module_logger = logging.getLogger(python_module_name)

    if log_to_stdout:
        module_logger.addHandler(console_handler)

    # Setting up file output
    if log_to_file:
        file_path = os.path.join(log_directory, python_module_name + '.log')
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(log_formatter)
        module_logger.addHandler(file_handler)

    module_logger.setLevel(logging_level)
    return module_logger

# Command System----------------------------------------------------------------
# TODO: Have it check for duplicate with general commands
def check_duplicate_command_name(name: str, channel: str='') -> bool:
    """Checks if a command is already registered by a module

    :param name: Name of the command
    :channel: If given, will check against custom channel-specific commands.
    :return: False if command is already in use, else it returns True.
    """

    # Checking against module registered commands
    for module in _MODULES.keys():
        if name.lower() in _MODULES[module]["commands"].keys():
            return False

    if channel:
        # Checking against custom, channel specific, commands.
        cursor.execute(
            "SELECT name FROM general_commands "
            "WHERE name=(?) AND channel=(?)", (name, channel)
        )

        if len(cursor.fetchall()) > 0:
            return False
    

    return True


def check_cooldown(
        name: str, user: IRC.User, module_name: str=''
) -> bool:

    # Checking module commands

    if module_name:
        try:
            commands_config = _MODULES[module_name.lower()]['commands_config']
            last_call = commands_config[user.chatted_from][name]['last_call_time']

            if user.is_mod or user.is_broadcaster:
                cooldown = commands_config[user.chatted_from][name]['mod_cooldown']
            else:
                cooldown = commands_config[user.chatted_from][name]['cooldown']

            if time.time() - last_call > cooldown:
                _logger.debug(
                    "Allowing user '{}' to run command '{}'.".format(user.name, name)
                )
                return True
            else:
                _logger.debug(
                    "Disallowing user '{}' from running command '{}'.".format(user.name, name)
                )
                return False
        except KeyError:
            pass
    else:

        # Checking channel-specific commands
        cursor.execute(
            "SELECT cooldown,last_call FROM general_commands "
            "WHERE name=(?) AND channel=(?)",
            (name, user.chatted_from)
        )

        data = cursor.fetchall()
        if len(data) == 0:
            # If there is no data, the command wasn't found so we return false.
            return False
        elif len(data) > 1:
            warnings.warn(
                "Duplicate custom command found!: name={}, channel={}"
                "".format(name, user.chatted_from)
            )
            # Returns false no matter what. I'd prefer it to not allow the running
            # of a command, so as to prompt someone to look into the bot and find
            # out what the problem is rather than thinking everything is alright.
            return False

        if user.is_mod or user.is_broadcaster:
            cooldown = DEFAULT_MOD_COOLDOWN
        else:
            cooldown = data[0][0]

        # data[0][1] is last_call
        if time.time() - data[0][1] > cooldown:
            _logger.debug(
                "Allowing user '{}' to run general command '{}' in channel '{}'.".format(
                    user.name, name, user.chatted_from
                )
            )
            return True
        else:
            _logger.debug(
                "Disallowing user '{}' from running general command '{}' in channel '{}'.".format(
                    user.name, name, user.chatted_from
                )
            )
            return False

    return False


def mark_cooldown(name: str, user: IRC.User, module_name: str=''):

    if module_name:
        try:
            # Updating module commands
            if user.is_mod or user.is_broadcaster:
                _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['last_mod_call_time'] = time.time()
            else:
                _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['last_call_time'] = time.time()
        except KeyError:
            pass
    else:
        # Updating channel-specific commands
        if user.is_mod or user.is_broadcaster:
            return  # So as to not affect the cooldown for other users
        else:
            cursor.execute(
                "UPDATE general_commands "
                "SET last_call=(?) "
                "WHERE name=(?) AND channel=(?)",
                (time.time(), name, user.chatted_from)
            )


def run_general_command(user: IRC.user):
    command = user.command.lower().split(DEFAULT_COMMAND_PREFIX)[0]
    
    cursor.execute(
        "SELECT user_level, response FROM general_commands "
        "WHERE name=(?) AND channel=(?)",
        (command, user.chatted_from.lower())
    )

    data = cursor.fetchall()
    if len(data) > 0:  # Checks to see if a command was returned by the database
        user_level = data[0][0]
        response = data[0][1]
        if check_user_level(user_level, user) and check_cooldown(command, user):
            # Send the response to the channel the command was run in.
            IRC.chat(user.chatted_from, response)
            mark_cooldown(command, user)
        

def run_command(module_name: str, user: IRC.User):
    # TODO: Consider doing a "try/except" block instead of looping through the
    #       commands. I just need to make the command manager not allow regex,
    #       which I think the '\w' command already does anyways. In doing so, I
    #       should be able to just attempt to run the command instantly rather
    #       than going through the entire dictionary.
    for regex, command in _MODULES[module_name.lower()]['commands'].items():
        # Only launches commands if they match exactly with the regex, if
        # the command starts later or ends with extra information it doesn't
        # launch. I did this so that we wouldn't run into issues where
        # someone might repeat the same command, causing the regex to
        # match multiple times and catching the module developers off guard.
        full_regex = r"^{}{}$".format(DEFAULT_COMMAND_PREFIX, regex.lstrip())

        # Check if regex (usually just a command name) matches.
        if re.match(full_regex, user.message):
            _logger.debug(
                "Regex '{}' has matched with user command '{}'.".format(
                    full_regex, user.message
                )
            )
            if check_cooldown(regex, user, module_name=module_name):
                _logger.info("Regex matched, running command '{}'".format(full_regex))
                # Run the command.
                command(user)

                # Update the cooldown information
                mark_cooldown(regex, user, module_name)

            # Exit out of the loop since we've matched the command and attempted
            # to run it.
            break

# TODO: Make sure this works!
def unregister_command(name: str) -> bool:
    """Removes a module command
    """
    module = get_module_name()
    if name in _MODULES[module]['commands'].keys() :
        del _MODULES[module]['commands_config'][name]
        del _MODULES[module]['commands'][name]
        return True
    else:
        return False


# TODO: Since adding regex, there's an issue with command duplication!
#       Someone can add both 'quote( \d+)?' and 'quote', both will match if a
#       user inputs '!quote', this is problematic. I was thinking that I could
#       split the first 'word' from the command name/regex and use that as a
#       sort of 'master command'. I could do re.sub('[^\w]|[^0-9]'), which would
#       remove the special regex characters, but that'd leave things like the
#       'd' from \d, and it would ruin the ability to use things like foreign
#       characters in a command name.
#
#       I think the easiest thing I could do is split by space, but that would
#       not work for something like 'quote\d+' (just an example).
#
#       Another thing I could do is split by any characters used in regex, I
#       only need to split once, just so that I can get the very first 'word'.
#
#           It would be something like this:
#           re.split(r'[<characters used in regex>]')
# NOTE: Maybe I can have an application give test input to see if their code
#       launches more than one command!
#
#       If I had the skill, I could probably create a complex system that could
#       fill in the regex areas, but that's very complicated (or seems that way)
#       and I'm unsure if I could ever make something like that. It's easier to
#       just request that a module give some test input, maybe when they
#       register their command they can give (possibly optional) input string.
#
#       We would just have one function go through each command available and
#       try to match the string. If it matches, it adds the regex and module
#       from which it matched to a dict. Then it moves on until it no longer
#       has any commands/modules to try and match against. If the dict is
#       larger than 1, it has failed and there is a duplicate command.
def register_command(
        name: str,
        function: callable,
        user_level=DEFAULT_USERLEVEL,
        cooldown=DEFAULT_COOLDOWN,
        mod_cooldown=DEFAULT_MOD_COOLDOWN,
        enabled=True,
):
    """Registers a command so that it may be used on Twitch.

    Registers a command as belonging to a specific module. The command is then
    available for use on Twitch. The command is then managed globally by the
    Command Manager, which can then manage changes to the cooldown, userlevel,
    and even disable the command (stops it from being run) if a broadcaster
    desires so.

    :param name: Name of the command you'd like to register
    :param function: Function that will be called when the command is used.
    :param user_level: The level necessary for a user to run the command.
    :param cooldown: Time, in seconds, before the command can be run again.
    :param mod_cooldown: Cooldown for moderators, also affects broadcaster.
    :param enabled: Whether or not the command is able to be used.
    :return: Nothing.
    """
    if not name:
        raise RuntimeError("Command attempted to register with empty string "
                           "for name.")
    elif not user_level:
        raise RuntimeError("Command attempted to register with an empty string "
                           "as its user_level.")
    elif cooldown < 5:
        warnings.warn(
            "Command '{}' has registered with a cooldown of {} seconds. "
            "This could be dangerous for your bot as it may get globally "
            "banned for spam.".format(cooldown, name)
        )

    global _MODULES
    # Make sure module has been registered before registering command
    module_name = get_module_name()
    if module_name.lower() not in _MODULES.keys():
        raise RuntimeError("Unregistered module '{}' attempted to register a "
                           "command. Please register your module "
                           "before registering commands.".format(module_name))

    # Make sure user_level is something we've implemented code for.
    if user_level not in USER_LEVELS:
        raise RuntimeError("Command attempted to register with unknown user "
                           "level. Value given: {} | Accepted values can be "
                           "found in USER_LEVELS list.".format(user_level))

    # Checking if command name is taken locally
    if not check_duplicate_command_name(name.lower()):
        raise RuntimeError("Command name '{}' is already taken.".format(name))
    else:
        print("Registering {} as a command for module {}".format(name, module_name))
        if '###DEFAULT###' not in _MODULES[module_name.lower()]["commands_config"]:
            _MODULES[module_name.lower()]["commands_config"]['###DEFAULT###'] = {}

        _MODULES[module_name.lower()]["commands_config"]['###DEFAULT###'][name.lower()] = {
            "userlevel": user_level,
            "last_call_time": 0,
            "mod_cooldown": mod_cooldown,
            "cooldown": cooldown
        }

        _MODULES[module_name.lower()]["commands"][name.lower()] = function


# Module Systems----------------------------------------------------------------
def update_modules_for_new_channel(channel: str):
    """Adds channels to module commands_config fields.
    :param channel: The channel that will be added to each module
    :return: Nothing
    """
    for module in _MODULES.keys():
        if channel not in _MODULES[module]["commands_config"]:
            default_command_config = _MODULES[module]["commands_config"]["###DEFAULT###"]
            _MODULES[module]["commands_config"][channel] = default_command_config

def check_duplicate_module_name(module_name: str) -> bool:
    """Checks if module name has already been registered.

    :param module_name: Name that will be checked against other modules.
    :return: False if name is already registered, else it returns True.
    """
    for module in _MODULES.keys():
        if module_name.lower() == module.lower():
            return False
    else:
        return True


def register_shutdown_function(function: callable):
    """Adds a function to a list of functinos that will be called on bot shutdown.
    """
    global _SHUTDOWN_FUNCTIONS
    _SHUTDOWN_FUNCTIONS.append(function)


def register_module(
        category: str="response",
):
    """Registers a module, allowing for management of commands and data.

    Registering a module adds it to a dictionary that is managed by the other
    module tools. This allows a module to register commands, which can then be
    run in Twitch chat.

    :param category: The category corresponding to what the module is meant for.
    :return: Nothing
    """
    module_name = get_module_name()

    if not category:
        raise RuntimeError("Module {} attempted to register with an empty "
                           "string for its category.".format(module_name))

    # Making sure category is one we know of
    if category.lower() not in CATEGORIES:
        raise RuntimeError("Module {} attempted to register with an unknown "
                           "category.".format(module_name))

    # Checking for duplicate module name.
    if not check_duplicate_module_name(module_name):
        raise RuntimeError("Module name {} is already registered".format(module_name))

    global _MODULES

    # Setting up storage for module
    module_storage = os.path.join(primary_storage_directory, module_name.lower())
    if not os.path.exists(module_storage):
        os.makedirs(module_storage)
    if module_name.lower() not in _MODULES.keys():
        # Loading in basic Module dictionary layout.
        # NOTE: I added "custom_commands" as a temporary fix for general
        #       commands made by the command_manager. However... I feel as if
        #       I'll need to rework this, but chances are that won't happen and
        #       this temporary fix will turn out permanent. - (2-28-2017)
        _MODULES[module_name.lower()] = {
            "category": category.lower(),
            "storage": module_storage,
            "commands_config": {},
            "commands": {}
        }


# Management Systems------------------------------------------------------------
# TODO: Remember to log when a user tries to access something they
#       don't have the level for.
def check_user_level(level: str, user: IRC.User) -> bool:
    """Compares twitch.User to the given (and known) userlevel

    The known userlevels are in the USER_LEVELS dict.

    :param level: Level that will be compared with the User's level.
    :param user: The twitch.User object.
    :return: True if levels match, else it returns False
    """
    if level == "moderation":
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


def moderation_check(user: IRC.User) -> bool:
    """Checks if user has triggered any moderation filters.

    Goes through all moderation modules and checks the user against all filters
    that are currently enabled for a channel.

    :param user: The twitch.User that will be passed to the moderation filters.
    :return: False if any filters get triggered, else it returns True.
    """
    # Mother of god... the if checks...
    for module_name in _MODULES.keys():
        if _MODULES[module_name]["category"] == "moderation":
            for command in _MODULES[module_name]["commands"].keys():
                if not _MODULES[module_name]["commands"][command](user):
                    return False
    return True


# TODO: Create run_command and run_command_manager
def manage_response_commands(user: IRC.User):
    """Runs a user's command if it is in a response modules.

    Checks if a command is enabled and if the user's level matches the level
    necessary to run a command. If both are true, the user is passed over to
    the command, so that it may be run.

    :param user: The user who is attempting to run a command.
    :return: Nothing
    """

    # Go through modules and attempt to run the command, if it doesn't exist
    # then nothing will happen.
    for module_name in _MODULES.keys():
        if _MODULES[module_name]["category"] == "response":
            run_command(module_name, user)


# Consider allowing people to disable the one ways? Since they'll do things like
# logging chat and gathering statistics,
# which some channels will not like.
def hand_over_to_one_ways(user: IRC.User):
    """Hands the user over to every one-way module.

    :param user: The user object that will be given to each module
    :return: Nothing
    """
    for module_name in _MODULES.keys():
        if _MODULES[module_name]["category"] == "one-way":
            for command in _MODULES[module_name]["commands"].values():
                # These aren't supposed to return anything, either way we don't
                # care to check if they do.
                command(user)


def run_shutdown_functions():
    for function in _SHUTDOWN_FUNCTIONS:
        function()
