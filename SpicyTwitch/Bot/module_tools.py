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
# TODO: Consider managing timer systems in a better way.
#       It feels like they could get their own set of categories?
# TODO: Work on timers. As I'm having a few issues with the system.
#       - Maybe I could just make a very simple system where the timer
#         manager just runs a command ?
# TODO: Add timer functionality
# TODO: Add docstrings to all functions
# TODO: BIG ISSUE, currently this system only works on a single channel!
#       I need to make it a multi-channel system! It needs to have configuration
#       on a per-channel basis.
# TODO: Read up on properly using python, some of the things I've done feel like
#       there may be better ways to do them.
# NOTE: It may be better to just use a database at this point. But for now this
#       can work.
# NOTE: I think if I use function decorators I can do some fun stuff, like maybe
#       that would be an easier thing to do than having users register their
#       commands?
# TODO: Check for cooldowns.
#       Also, I just should put something like a 5 second cooldown for mods(?).
# TODO: Find a way to get the module __name__ instead of asking for it.
#       This way, functions like log_info won't need to request the module name.
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
# TODO: Log exceptions be converting them to str().
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
# NOTE: As I thought, logging with these functions prints the module as
#       module_tools instead of the respective module.
# TODO: Fix logging.
# NOTE: I could just have a single bool called "logging_on" that all modules
#       should check before they assign their handlers...
# Imports-----------------------------------------------------------------------
import time
import inspect  # May ruin compatibility with anything other than CPython!
import re
import logging
import warnings
import platform
import os
import yaml  # TODO: Add to requirements file.
import twitch


# Global Variables--------------------------------------------------------------
# Configuration
DEFAULT_COMMAND_PREFIX = '!'
USER_LEVELS = ["moderator", "broadcaster", "subscriber", "everyone"]
CATEGORIES = ["moderation", "response", "one-way", "timer"]
DEFAULT_COOLDOWN = 30
DEFAULT_MOD_COOLDOWN = 5
DEFAULT_USERLEVEL = "everyone"
DEFAULT_COMMAND_CONFIG = {
    "enabled": True,
    "userlevel": "everyone",
    "last_mod_call_time": 0,
    "last_call_time": 0,
    "mod_cooldown": DEFAULT_MOD_COOLDOWN,
    "cooldown": DEFAULT_COOLDOWN
}

# Logging
log_to_file = True
logging_level = logging.INFO
log_format = '[%(asctime)s] [%(levelname)s] [%(module)s] (%(funcName)s): ' \
             '%(message)s'
date_format = '%Y/%m/%d %I:%M:%S %p'

# Modules and Systems
# Apparently no performance issues with having everything in one dictionary!
# Well, no issues as far as lookup time goes.
_MODULES = {}

# This list is what certain functions will use so that they don't modify the
# contents of these keys.
_IGNORE = ["storage", "category", "commands"]

# Cooldown for saving data
SAVE_COOLDOWN = 10
LAST_SAVE = 0


# Inspection--------------------------------------------------------------------
# TODO: Implement these functions!
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


def get_function_name(outer_module: bool=True) -> str:
    stack = inspect.stack()

    if outer_module:
        stack_index = 2
    else:
        stack_index = 1

    return stack[stack_index][3]

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

print(
    "Storage directory has been set to: {}".format(primary_storage_directory)
)

if not os.path.exists(primary_storage_directory):
    # Please don't come back to bite me in the butt...
    os.makedirs(primary_storage_directory)
    print(
        "Primary storage path did not exist, creating folders."
    )


log_directory = os.path.join(primary_storage_directory, "logs")
if log_to_file and not os.path.exists(log_directory):
    os.makedirs(log_directory)


# TODO: This is rather unnecessary now, I should remove it.
# For modules to be able to know what their storage directory is.
def _get_storage_directory(module_name: str='') -> str:
    if not module_name:
        module_name = get_module_name()

    try:
        if module_name.lower() in _MODULES.keys():
            directory = _MODULES[module_name.lower()]["storage"]

            print(
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


def load_module_information(module_name: str) -> bool:
    module_information = {}
    for directory in os.listdir(primary_storage_directory):
        if os.path.isdir(directory) and module_name.lower() in directory:
            for file_path in os.listdir(directory):
                with open(file_path, 'r') as file:
                    try:
                        key = file_path.split('_', 1)[-1]
                        module_information[key] = yaml.safe_load_all(file)
                    except IndexError:
                        continue

    if not module_information:
        print(
            "No saved data was found for the module {}.".format(module_name)
        )
        return False
    else:
        print(
            "Loaded saved data for module {}.".format(module_name)
        )

        _MODULES[module_name.lower()] = module_information
        return True


def recursive_yaml_load(directory_path: str) -> dict:
    pass


def recursive_yaml_dump(directory: str, data: dict):
    for key, value in data.items():
        if isinstance(value, dict):
            recursive_yaml_dump(value)
        else:
            # TODO: Setup yaml to safely dump data
            print("{0} : {1}".format(key, value))


def save_module_information(module_name: str):
    try:
        for info_key in _MODULES[module_name.lower()].keys():
            if info_key in _IGNORE:
                continue  # ignore the key and move onto the next one.

            data = _MODULES[module_name.lower()][info_key]

            file_name = "{}_{}.yaml".format(module_name.lower(), info_key)
            module_storage = _MODULES[module_name.lower()]['storage']
            file_path = os.path.join(module_storage, file_name)
            with open(file_path, 'w') as info_file:
                yaml.dump_all(data, info_file)

        print("Saved data for module {}".format(module_name))
    except KeyError:
        # TODO: Log error with module name
        pass


# TODO: When ready, add saving for other module categories.
def save_all():
    global LAST_SAVE
    for module in _MODULES.keys():
        if _MODULES[module]['category'] == 'response':
            save_module_information(module)

    LAST_SAVE = time.time()


# Logging System----------------------------------------------------------------
def create_logger(python_module_name: str='') -> logging.Logger:
    """Creates a logger with the module's __name__ and adds it to a local dict.

    Creates a logger using the logging module, using getLogger() with the input
    of the python_module_name argument. If python_module_name is not given, the
    function will attempt to determine the name of the module that called it.

    :param python_module_name:  The name used to create the logger. __name__
                                is recommended.
    :return: logging.Logger object
    """

    if not python_module_name:
        python_module_name = get_module_name()

    # Creating the logger
    module_logger = logging.getLogger(python_module_name)

    # Setting up formatter
    main_formatter = logging.Formatter(log_format, datefmt=date_format)

    # Setting up terminal/console output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(main_formatter)
    module_logger.addHandler(console_handler)

    # Setting up file output
    if log_to_file:
        file_path = os.path.join(log_directory, python_module_name)
        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(main_formatter)
        module_logger.addHandler(file_handler)

    module_logger.setLevel(logging_level)
    return module_logger


# Configuration ----------------------------------------------------------------
# TODO: In allowing a channel to change the config, add only their changes to
#       commands_config, so as to not create a huge amount of duplicates(?)
def get_config(channel: str, module_name: str='') -> dict:
    """Gets current state of channel's configuration settings for a module.

    Configuration options can be edited by moderators and broadcasters, which
    allows your module to react differently based on changes to specific
    options.

    :param module_name: Name of your registered module
    :param channel: The channel
    :return: A dictionary containing the configuration options.
    """

    if not module_name:
        module_name = get_module_name()

    try:
        return _MODULES[module_name.lower()]['config'][channel]
    except KeyError:
        pass  # TODO: Log error with either bad module name or channel name.


def update_config(channel: str, config: dict, module_name: str=''):
    if not module_name:
        module_name = get_module_name()

    try:
        _MODULES[module_name.lower()]['config'][channel] = config
    except KeyError:
        pass  # TODO: Log error with either bad module name or channel name.


# Data Management---------------------------------------------------------------
def get_data(channel: str, module_name: str='') -> dict:
    if not module_name:
        module_name = get_module_name()

    try:
        return _MODULES[module_name.lower()]['data'][channel.lower()]
    except KeyError:
        return {}  # TODO: Log error with either bad module name or channel name.


def update_data(channel: str, data: dict, module_name: str=''):
    if not module_name:
        module_name = get_module_name()

    try:
        _MODULES[module_name.lower()]['data'][channel] = data
    except KeyError:
        pass  # TODO: Log error with either bad module name or channel name.


# Command System----------------------------------------------------------------
def check_duplicate_command_name(name: str) -> bool:
    """Checks if a command is already registered by a module

    :param name: Name of the command
    :return: False if command is already in use, else it returns True.
    """
    for module in _MODULES.keys():
        if name.lower() in _MODULES[module]["commands"].keys():
            return False
    else:  # If we reach the end of the loop and nothing happens, return True.
        return True


def check_cooldown(module_name: str, name: str, user: twitch.User) -> bool:
    try:
        last_call = _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['last_call_time']

        if user.is_mod or user.is_broadcaster:
            cooldown = _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['mod_cooldown']
        else:
            cooldown = _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['cooldown']

        if time.time() - last_call > cooldown:
            return True
        else:
            return False
    except KeyError:
        # TODO: Log specific error
        return False


def mark_cooldown(module_name: str, name: str, user: twitch.User):
    if user.is_mod or user.is_broadcaster:
        _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['last_mod_call_time'] = time.time()
    else:
        _MODULES[module_name.lower()]['commands_config'][user.chatted_from][name]['last_call_time'] = time.time()


def run_command(module_name: str, user: twitch.User):
    for regex, command in _MODULES[module_name.lower()]['commands'].items():
        # Make sure the command is enabled
        enabled = _MODULES[module_name.lower()]["commands_config"][user.chatted_from][regex]['enabled']

        # Only launches commands if they match exactly with the regex, if
        # the command starts later or ends with extra information it doesn't
        # launch. I did this so that we wouldn't run into issues where
        # someone might repeat the same command, causing the regex to
        # match multiple times and catching the module developers off guard.
        full_regex = r"^{}{}$".format(DEFAULT_COMMAND_PREFIX, regex.lstrip())


        # Check if regex (usually just a command name) matches.
        if re.match(full_regex, user.message):
            if check_cooldown(module_name, regex, user):
                # Run the command.
                command(user)

                # Update the cooldown information
                mark_cooldown(module_name, regex, user)


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
def register_command(
        name: str,
        function: callable,
        user_level=DEFAULT_USERLEVEL,
        cooldown=DEFAULT_COOLDOWN,
        mod_cooldown=DEFAULT_MOD_COOLDOWN,
        enabled=True,
        module_name: str=''
):
    """Registers a command so that it may be used on Twitch.

    Registers a command as belonging to a specific module. The command is then
    available for use on Twitch. The command is then managed globally by the
    Command Manager, which can then manage changes to the cooldown, userlevel,
    and even disable the command (stops it from being run) if a broadcaster
    desires so.

    :param module_name: Name of your registered module
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
        raise RuntimeError("Command attempted to register with no user_level.")
    elif cooldown < 5:
        warnings.warn(
            "Command '{}' has registered with a cooldown of {} seconds. "
            "This could be dangerous for your bot as it may get globally "
            "banned for spam.".format(cooldown, name)
        )

    global _MODULES
    # Make sure module has been registered before registering command
    if not module_name:
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
        _MODULES[module_name.lower()]['commands_config'][name.lower()] = {}
        _MODULES[module_name.lower()]["commands_config"][name.lower()]["default"] = {
            "enabled": enabled,
            "userlevel": user_level,
            "last_call_time": 0,
            "mod_cooldown": mod_cooldown,
            "cooldown": cooldown
        }

        _MODULES[module_name.lower()]["commands"][name.lower()] = function


# Module Systems----------------------------------------------------------------
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


def update_modules_for_new_channel(channel: str):
    """Adds channels to module data/config/commands_config/etc.. fields.

    :param channel: The channel that will be added to each module
    :return: Nothing
    """
    for module in _MODULES.keys():
        for key, value in _MODULES[module].items():
            if key in _IGNORE:
                continue

            if channel not in value:
                if key == "commands_config":
                    _MODULES[module][key][channel] = {}
                    for command in _MODULES[module]["commands"].keys():
                        _MODULES[module][key][channel][command] = DEFAULT_COMMAND_CONFIG
                elif key == "config":
                    _MODULES[module][key][channel] = _MODULES[module][key]["DEFAULT_CONFIGURATION"]
                elif key == "data":
                    _MODULES[module][key][channel] = _MODULES[module][key]["DEFAULT_DATA_INITIALIZATION"]
                else:
                    _MODULES[module][key][channel] = {}


def register_module(
        data: dict=None,
        config: dict=None,
        category: str="response",
        module_name: str=''
):
    """Registers a module, allowing for management of commands and data.

    Registering a module adds it to a dictionary that is managed by the other
    module tools. This allows a module to register commands, which can then be
    run in Twitch chat, as well as making the command available to the Command
    Manager, which can then make changes to the commands cooldown and user level
    directly from Twitch (only managers and broadcasters can do this).

    The Command Manager also allows for changes to configuration options for
    the registered module. This allows a module to dynamically alter what it
    does based on changes to a specific configuration option.

    :param module_name: Name of the soon-to-be registered module
    :param category: The category corresponding to what the module is meant for.
    :param data: Data that will be used when initializing channels.
    :param config: Your default set of configuration options.
    :return: Nothing
    """
    if not module_name:
        module_name = get_module_name()


    if not category:
        raise RuntimeError("Module {} attempted to register with an empty "
                           "string for its category.".format(module_name))
    elif not isinstance(category, str):
        raise RuntimeError("Module category must be a string.")

    # Making sure category is one we know of
    if category.lower() not in CATEGORIES:
        raise RuntimeError("Module {} attempted to register with an unknown "
                           "category.".format(module_name))

    # Checking for duplicate module name.
    if not check_duplicate_module_name(module_name):
        raise RuntimeError("Module name {} is already used by another "
                           "module.".format(module_name))

    global _MODULES

    # Setting up storage for module
    module_storage = os.path.join(primary_storage_directory, module_name.lower())
    if not os.path.exists(module_storage):
        os.makedirs(module_storage)
    else:
        loaded_data = load_module_information(module_name.lower())

        if loaded_data:
            _MODULES[module_name.lower()] = loaded_data

    if module_name.lower() not in _MODULES.keys():
        if config:
            default_config = config
        else:
            default_config = {}

        if data:
            default_data = data
        else:
            default_data = {}

        # Loading in basic Module dictionary layout.
        _MODULES[module_name.lower()] = {
            "category": category.lower(),
            "storage": module_storage,
            "data": {"DEFAULT_DATA_INITIALIZATION": default_data},
            "config": {"DEFAULT_CONFIGURATION": default_config},
            "commands_config": {},
            "commands": {}
        }


# Management Systems------------------------------------------------------------
# TODO: Remember to log when a user tries to access something they
#       don't have the level for.
def check_user_level(level: str, user: twitch.User) -> bool:
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


def moderation_check(user: twitch.User) -> bool:
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
                if _MODULES[module_name]["commands_config"][user.chatted_from][command]["enabled"]:
                    if not _MODULES[module_name]["commands"][command](user):
                        return False
    return True


# TODO: Create run_command and run_command_manager
def manage_response_commands(user: twitch.User):
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
def hand_over_to_one_ways(user: twitch.User):
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