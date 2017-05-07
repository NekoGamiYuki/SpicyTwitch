# Imports-----------------------------------------------------------------------
import sqlite3
import os
import re
from time import time
from ... import irc
from ... import log_tools

# Global Variables--------------------------------------------------------------
_logger = log_tools.create_logger()


# Classes-----------------------------------------------------------------------
# TODO: Consider making the cooldown checker a parameter as well. This way, the
#       user can provide the following:
#           - Default cooldowns (Example: {'mod': 5, 'everyone': 30})
#           - Cooldown checker: callable
class Command(object):
    """A self contained Twitch IRC bot command interface.

    This class contains the necessary components for managing a Twitch IRC bot 
    command. It manages user level validation and cooldowns for multiple channels.

    :param name: The name of the command.
    :param command_function: The function that will be called when cooldownd and
                             user level allow for it.
    :param user_level: The user level necessary to run the command
    :param everyone_cooldown: The base cooldown that affects general users.
    :param mod_cooldown: The cooldown that affects mods and the broadcaster.
    :param valid_user_levels: A list of valid user levels that the command accepts.
    :param user_level_validator: A function that will be called to valid a user's
                                 level.
    :param ignore_casing: Used by other functions to determine whether or not the
                          command requires strict casing in order to be launched.
    """
    def __init__(
        self,
        name: str,
        command_function: callable,
        user_level: str,
        everyone_cooldown: int,
        mod_cooldown: int,
        valid_user_levels: list,
        user_level_validator: callable,
        ignore_casing: bool=False
    ):
        # Make sure name is not blank.
        if not name:
            raise ValueError("Name must not be blank")
        else:
            self.name = name

        # Set userlevel
        self.valid_user_levels = valid_user_levels
        if user_level.lower() not in self.valid_user_levels:
            levels = ''
            for level in self.valid_user_levels:
                levels += level+' '
            raise ValueError(
                "User level unrecognized. Please use one of the following: {}"
                "".format(levels)
            )
        else:
            self.user_level = user_level.lower()

        # Setup cooldown
        if everyone_cooldown < 0 or mod_cooldown < 0:
            raise ValueError("Cooldowns must not be negative")
        else:
            self.mod_cooldown = mod_cooldown
            self.everyone_cooldown = everyone_cooldown

        self.command_function = command_function
        self.user_level_validator = user_level_validator
        self.ignore_casing = ignore_casing
        self.channel_cooldowns = {}


    def check_cooldown(self, user: irc.User) -> bool:
        """Checks cooldown of command to see if enough time has passed.

        :param user: An irc.User object that will be used to check user levels.
        :returns: True if enough time has passed to run the command, else false.
        """

        # Initializing cooldown counting for any new channel
        if user.chatted_from not in self.channel_cooldowns:
            _logger.debug("Initializing cooldown for new channel '{}'.".format(
                    user.chatted_from
                )
            )
            self.channel_cooldowns[user.chatted_from] = {
                "mod": 0,
                "everyone": 0
            }

        if user.is_mod or user.is_broadcaster:
            _logger.debug("Use was mod/broadcaster")
            last_mod_call = self.channel_cooldowns[user.chatted_from]["mod"]
            if time() - last_mod_call > self.mod_cooldown:
                _logger.debug("Cooldown has passed")
                return True
            else:
                _logger.debug("Cooldown is still in effect")
                return False
        else:
            _logger.debug("User was not a mod/broadcaster")
            last_everyone_call = self.channel_cooldowns[user.chatted_from]["everyone"]
            if time() - last_everyon_call > self.everyone_cooldown:
                _logger.debug("Cooldown has passed")
                return True
            else:
                _logger.debug("Cooldown is still in effect")
                return False


    def check_user_level(self, level: str, user: irc.User) -> bool:
        """Compares irc.User object to commands userlevels

        :returns: True if userlevel meets command criteria.
        """
        _logger.debug("Checking user level for: '{}' in channel '{}'".format(
                user.name, user.chatted_from
            )
        )
        return self.user_level_validator(level, user)


    # NOTE: This is not meant to be called by users! This is just something that an
    #       interface for a bot may find useful.
    def change_user_level(self, level: str) -> bool:
        """Changes the user level of the command

        :returns: True if the level is valid and is changed.
        """
        if level.lower() not in self.valid_user_levels:
            _logger.debug("User level '{}' was not valid for command '{}'.".format(level))
            return False
        else:
            _logger.debug("Changing userlevel of '{}' to '{}'".format(self.name, level))
            self.user_level = level.lower() 
            return True
        

    def mark_last_call(self, user: irc.User):
        """Marks the last call of the command for use in check_cooldown

        Sets different variables based on whether or not the user is a/the
        moderator/broadcaster.
        """
        if user.is_mod or user.is_broadcaster:
            _logger.debug("Marking mod cooldown for channel '{}' and command '{}'".format(
                    user.chatted_from, self.name
                )
            )
            self.channel_cooldowns[user.chatted_from]["mod"] = time()
        else:
            _logger.debug("Marking everyone cooldown for channel '{}' and command '{}'".format(
                    user.chatted_from, self.name
                )
            )
            self.channel_cooldowns[user.chatted_from]["everyone"] = time()


    def run(self, user: irc.User) -> bool:
        """Runs the command if cooldown and userlevel allow it.

        :returns: True if the command was able to be ran
        """
        _logger.debug("Attempting to run command '{}' in channel '{}'".format(
                self.name, user.chatted_from
            ) 
        )
        if self.check_cooldown(user) and self.check_user_level(self.user_level, user):
            _logger.debug("Cooldown and userlevel have checked out. Running command.")
            self.command_function(user)
            self.mark_last_call(user)
            return True
        else:
            _logger.debug("Cooldown and userlevel have not checked out. Will not run command.")
            return False


# NOTE: For timers meant to only be in one channel, simply have the channels list 
#       contain a single channel.
class Timer(object):
    """Runs a function for multiple channels after an alloted amount of time passes

    :param name: Name of the timer.
    :param function: The function that will be called
    :param cooldown: The amount of time that needs to pass (in seconds) before the
                     function is allowed to run again
    :param channels: A list of channels that will be iterated through every time the
                     function is allowed to run.
    """
    def __init__(self, name: str, function: callable, cooldown: int, channels: list):

        if cooldown < 0:
            raise ValueError("Cooldown must not be negative")
        else:
            self.cooldown = cooldown 

        self.name = name
        self.function = function
        self.last_call = 0
        self.channels = channels


    def check_cooldown(self) -> bool:
        """Checks if enough time has passed since the last run

        :returns: True if enough time has passed
        """
        if time() - self.last_call > cooldown:
            return True
        else:
            return False


    def mark_last_call(self):
        """Updates the last_call variable to state when the timer was last ran."""
        self.last_call = time.time()


    def run(self) -> bool:
        """Checks cooldown and runs the timer if allowed to.

        :returns: True if the timer runs.
        """
        if self.check_cooldown():
            for channel in self.channels:
                self.function(channel)
            self.mark_last_call()
            return True
        else:
            return False


# Modules ----
class CommandModule(object):
    """A class for managing mutliple commands
    """
    def __init__(self, name: str, command_prefix: str, storage_directory: str=''):
        self.name = name
        self.commands = {}
        self.command_prefix = command_prefix
        self.storage_directory = storage_directory


    def check_if_command_exists(self, command_name: str, ignore_casing: bool=False) -> bool:
        for name, single_command in self.commands.items():
            if single_command.ignore_casing or ignore_casing:
                if command_name.lower() == name.lower():
                    return True
            elif name == command_name:
                    return True

        return False 

    def add_command(self, command: Command) -> bool:
        """Adds a command to the command dictionary

        :param command: A Command object that will be added to the commands dict.
        :returns: True if the command is not a duplicate and is added, else false.
        """
        if self.check_if_command_exists(command.name, command.ignore_casing):
            return False
        else:
            self.commands[command.name] = command 
            return True


    def remove_command(self, command_name: str) -> bool:
        """Removes a command from the commands dictionary

        :param command_name: Name of the command that will be removed
        :returns: True if the command was removed.
        """
        try:
            del self.commands[command_name]
            return True
        except KeyError:
            return False


    def run_command(self, user: irc.User) -> bool:
        """Attemps to run a command if it matches with the user's message

        Creates a simple regex that includes the command prefix given when
        the class object is created. If the command allows for it, it also 
        lowercases the both the command name/regex and the user's message 
        so as to not worry about casing differences.

        :param user: The user whose message will be checked against to see if
                     they're using a command that is in this module.
        :returns: True if the command was able to run
        """
        for name, command in self.commands.items():
            if command.ignore_casing:
                name = name.lower()
                message = user.message.lower()
            else:
                message = user.message

            # NOTE: I escaped the DEFAULT_COMMAND_PREFIX in case someone changes
            #       it, so as to not have it accidentally counted as a regex character.
            full_regex = '^\{}{}$'.format(
                self.command_prefix, name
            )
            if re.match(full_regex, message):
                return command.run(user)

        # If we go through every command and match nothing
        return False
            
                

class ModerationModule(object):
    def __init__(self, name: str):
        self.name = name
        self.filters = []

    def check(self, user: irc.User):
        """Goes through every filter and checks a users message against them

        :returns: False if one of the filters is triggered. True if all is good.
        """
        for moderation_filter in filters:
            if not moderation_filter(user):
                return False
        return True 


# Databases ----
class GeneralCommandDatabase(object):
    def __init__(self, name: str, storage_location: str=''):

        # Storage setup
        if not storage_location:
            self.storage_location = 'Ram'
            self.database_location = ':memory:'
        else:
            self.storage_location = storage_location
            self.database_location = os.path.join(
                self.storage_location, 'general_commands.db'
            )

        if not os.path.exists(self.storage_location):
            os.mkdir(self.storage_location)

        # Setting name
        if not name:
            raise ValueError("Name must not be blank")
        else:
            self.name = name


        # Setting up database
        self.database = sqlite3.connect(self.database_location)
        self.cursor = self.database.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS general_commands "
            "(name TEXT, response TEXT, cooldown INT, user_level TEXT, channel TEXT)"
        )
        self.channel_cooldowns = {}

    def initialize_channel(self, channel: str):
        if channel.lower() not in self.channel_cooldowns.keys():
            self.channel_cooldowns[channel.lower()] = {}

    # NOTE: Not meant to be called repeatedly! Instead this should be called
    #       on startup, to remove any possibly conflicting commands if an update
    #       has been made to the bot.
    def remove_these_commands(
        self, command_names: list, remove_from: list=[]
    ):

        # Copy into variable so as to not modify parameter.
        channels = remove_from

        if not channels:
            for command in command_names:
                if isinstance(str, command):
                    self.cursor.execute(
                        "DELETE FROM general_commands "
                        "WHERE name=(?)"

                    )

                else:
                    pass # TODO: DEBUG log that an item was skipped
        else:
            for channel in channels:
                if isinstance(str, channel):
                    for command in command_names:
                        if isinstance(str, command):
                            self.cursor.execute(
                                "DELETE FROM general_commands "
                                "WHERE name=(?) AND channel=(?)",
                                (command.lower(), channel.lower())

                            )

                        else:
                            pass # TODO: DEBUG log that an item was skipped
                else:
                    pass

        self.database.commit()


    def check_for_duplicates(self, command_name: str, channel: str=''):
        """Checks if a command name is in the database

        :param channel: A specific channel to check
        :returns: True if it is, False if it isn't
        """
        if channel:
            self.cursor.execute(
                "SELECT * FROM general_commands "
                "WHERE name=(?) AND channel=(?)",
                (command_name.lower(), channel.lower())
            )
        else:
            self.cursor.execute(
                "SELECT * FROM general_commands "
                "WHERE name=(?)",
                (command_name.lower(),)
            )

        data = self.cursor.fetchall()
        if len(data) > 0:
            return True
        else:
            return False


    def add_command(
        self, 
        command_name: str,
        response: str,
        cooldown: int,
        user_level: str,
        channel: str
    ) -> bool:
        """Adds a command to the database if it does not already exist

        :param command_name: The name of the command (The one users will use)
        :param response: What will be shown when the command is ran
        :param cooldown: How long to wait before allowing the command to be ran again
        :param user_level: The required level (such as 'moderator') for a user to be
                           able to run the command
        :param channel: The channel this command is being made for.
        :returns: True if the command was added, False if it already exists.
        """

        if cooldown < 0:
            raise ValueError("Cooldown must not be negative")

        if self.check_for_duplicates(command_name, channel):
            return False
        else:
            command_name = command_name.lower()
            user_level = user_level.lower()
            channel = channel.lower()

            self.cursor.execute(
                "INSERT INTO general_commands "
                "(name, response, cooldown, user_level, channel) "
                "VALUES (?,?,?,?,?)",
                (command_name, response, cooldown, user_level, channel)
            )
            self.database.commit()
            return True

    def check_cooldown(self, command_name: str, channel: str) -> bool:
        """Checks if enough time has passed since the last time a command was ran.

        :param command_name: The command that will be 
        """
        self.cursor.execute(
            "SELECT cooldown FROM general_commands "
            "WHERE name=(?) AND channel=(?)",
            (command_name.lower(), channel.lower())
        )

        data = self.cursor.fetchall()

        if not data:
            return False
        else:
            try:
                cooldown = data[0][0]
                last_call = self.channel_cooldowns[channel][command_name.lower()]

                if time() - last_call > cooldown:
                    return True
                else:
                    return False
            except KeyError:
                # This assumes that the command is new and therefor hasn't had its
                # cooldown marked. Hopefully this doesn't end badly...
                return True


    def mark_cooldown(self, command_name: str, channel: str) -> bool:
        self.cursor.execute(
            "SELECT * FROM general_commands "
            "WHERE name=(?) AND channel=(?)",
            (command_name.lower(), channel.lower())
        )

        data = self.cursor.fetchall()
        if not data:
            return False
        else:
            self.channel_cooldowns[channel][command_name.lower()] = time()
            return True

    
    def get_user_level(self, command_name: str, channel: str) -> str:
        """Returns the user level of a command

        :param command_name: The name of the command whose user level will be returned
        :param channel: The channel the command belongs to.
        """
        self.cursor.execute(
            "SELECT user_level FROM general_commands "
            "WHERE name=(?) AND channel=(?)",
            (command_name.lower(), channel.lower())
        )

        data = self.cursor.fetchall()

        if not data:
            return ''
        else:
            return data[0][0]


    def get_response(self, command_name: str, channel: str) -> str:
        """Returns the response of a command

        :param command_name: The name of the command whose user level will be returned
        :param channel: The channel the command belongs to.
        """
        self.cursor.execute(
            "SELECT response FROM general_commands "
            "WHERE name=(?) AND channel=(?)",
            (command_name.lower(), channel.lower())
        )

        data = self.cursor.fetchall()

        if not data:
            return ''
        else:
            return data[0][0]

    
    def close(self):
        sefl.cursor.close()
        self.database.close()
