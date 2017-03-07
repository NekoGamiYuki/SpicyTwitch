"""
This module will manage two main parts of the system.

First:
It will manage configuration of every other command module
"""
# TODO: I just realized something pretty terrible... Registering commands with
#       the create_command() function will make the command available on every
#       channel this bot is on... So really, I can't do it this way. Instead I
#       should use the data from module_tools

# Imports---------------------------------------------------------------------
import re
from .. import irc
from . import module_tools

# Global Variables--------------------------------------------------------------
loaded_channels = []
default_data = {'commands': {}}


# Regex-----------------------------------------------------------------------
# TODO: I believe I need to do a check at the start of each regex.
#       I'll check for a character as that's what'll be used to denote a call.
add_regex = re.compile(r"commands add (--\w+=\w+)? (\w+) (\w+|\W+)")
edit_regex = re.compile(r"commands edit (--\w+=\w+)? (\w+) (\w+|\W+)")
delete_regex = re.compile(r"commands (delete|remove) (\w+)")
rename_regex = re.compile(r"commands rename (\w+)")
config_regex = re.compile(r"config edit (\w+) (\w+) (\w+)")


# Module Registration-----------------------------------------------------------
module_tools.register_module(default_data)
logger = module_tools.create_logger()


# Command Creation--------------------------------------------------------------
def save_command(
        channel: str, name: str, response: str, user_level: str, cooldown: int
):
    data = module_tools.get_data(channel)
    commands = data['commands']
    if name not in commands.keys():
        commands[name] = {
            "response": response,
            "user_level": user_level,
            "cooldown": cooldown
        }

    data['commands'] = commands
    module_tools.update_data(channel, data)


def create_command(
        channel: str, name: str, response: str, user_level: str, cooldown: int
):
    def response_function(user: irc.User):
        irc.chat(response, channel)

    response_function.__name__ = name

    # TODO: Look into possible issues that might come from this, as the ability
    #       for a twitch user to register a command with regex is powerful but
    #       might lead to some issues... I could add a safety check and force
    #       users to not use regex by splitting by non-ascii characters, but
    #       I feel like that wouldn't be a good idea. Maybe I could add a 'test'
    #       option for the command. Like a user can do -test=INPUT and that'll
    #       test the command up against a bunch of other commands?
    if user_level == "moderator" or user_level == "broadcaster":
        module_tools.register_command(
            name,
            response_function,
            user_level=user_level,
            mod_cooldown=cooldown,
            channel=channel
        )
    else:
        module_tools.register_command(
            name,
            response_function,
            user_level=user_level,
            cooldown=cooldown,
            channel=channel
        )

    save_command(channel, name, response, user_level, cooldown)


# TODO: Make a function that loops through irc.channels.keys() and attempts to
#       load all
def load_all():
    global loaded_channels

    for channel in irc.channels.keys():
        if channel not in loaded_channels:
            logger.info("Loading commands for channel '{}'.".format(channel))

            data = module_tools.get_data(channel)
            for command_name, command_data in data['commands'].items():
                create_command(
                    channel,
                    command_name,
                    command_data["response"],
                    command_data["user_level"],
                    command_data["cooldown"]
                )

            loaded_channels.append(channel)


# Command Functions-------------------------------------------------------------
def commands_add(user: irc.User):
    parsed_input = add_regex.findall(user.message)

    options = {}
    if len(parsed_input) >= 3:
        for option in parsed_input[:-2]:
            option_value = option.split('=', 1)

            if len(option_value) < 2:
                continue

            options[option[0].split('-', 1)[1].lower()] = option_value[1]

    command_name = parsed_input[-2]
    command_response = parsed_input[-1]

    if not module_tools.check_duplicate_command_name(command_name):
        user.send_message("The name {} is already in use.".format(command_name))
    else:
        if 'userlevel' in options.keys():
            level = options['userlevel']
        else:
            level = 'everyone'

        if "cooldown" in options.keys():
            cooldown = options['cooldown']
        else:
            cooldown = 30

        create_command(
            user.chatted_from, command_name, command_response, level, cooldown
        )

