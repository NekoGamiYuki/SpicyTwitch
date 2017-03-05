# Imports-----------------------------------------------------------------------
import re
from random import choice
from .. import irc
from . import module_tools

# Global Variables--------------------------------------------------------------
# Decided to use a local variable for storage instead of the module_tools
# storage system since I don't intend to have any of this data saved. The one
# downside is that now I have to manage channels myself.
sacrifices = {}

# Regex-------------------------------------------------------------------------
main_regex = r"sacrifice( subs|mods)?"
reset_regex = r"sacrifice reset"


# Module Registration-----------------------------------------------------------
module_tools.register_module()

# Getting a logger
logger = module_tools.create_logger()


# Ease of use-------------------------------------------------------------------
def check_channel(channel: str):
    global sacrifices

    if channel not in sacrifices.keys():
        sacrifices[channel] = {'subs': [], 'mods': [], 'everyone_else': []}


# Command functions-------------------------------------------------------------
def sacrifice_me(user: irc.User):
    check_channel(user.chatted_from)

    global sacrifices

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']

    if user.is_mod and user.name.lower() not in mods:
        sacrifices[user.chatted_from]['mods'].append(user.name.lower())
    elif user.is_sub and user.name.lower() not in subs:
        sacrifices[user.chatted_from]['subs'].append(user.name.lower())
    else:
        sacrifices[user.chatted_from]['everyone_else'].append(user.name.lower())


def sacrifice_count(user: irc.User):
    check_channel(user.chatted_from)

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']
    everyone = sacrifices[user.chatted_from]['everyone_else'] + subs + mods

    count = len(everyone)
    if count <= 0:  # Should never be less than Zero, but I'd rather be safe.
        user.send_message("Nobody has offered themselves as a sacrifice.")
    else:
        irc.chat("There are {} soon-to=be sacrifices!".format(count),
                 user.chatted_from)


def sacrifice_reset(user: irc.User):
    check_channel(user.chatted_from)

    sacrifices[user.chatted_from] = {
        'subs': [], 'mods': [], 'everyone_else': []
    }

    user.send_message("List of sacrifices has been cleared.")


def sacrifice(user: irc.User):
    check_channel(user.chatted_from)

    parsed_input = re.findall(main_regex, user.message)

    if len(parsed_input) > 1:
        option = parsed_input[-1].lower()
    else:
        option = ''

    subs = sacrifices[user.chatted_from]['subs']
    mods = sacrifices[user.chatted_from]['mods']
    everyone = sacrifices[user.chatted_from]['everyone_else'] + subs + mods

    if option:
        if option == 'subs':
            if subs:
                todays_sacrifice = choice(subs)
                user.send_message(
                    "Subscriber sacrifice is @{}".format(todays_sacrifice)
                )
            else:
                user.send_message(
                    "No subscribers have offered themselves as a sacrifice."
                )
        elif option == 'mods':
            if subs:
                todays_sacrifice = choice(mods)
                user.send_message(
                    "Moderator sacrifice is @{}".format(todays_sacrifice)
                )
            else:
                user.send_message(
                    "No moderators have offered themselves as a sacrifice."
                )
    else:
        if everyone:
            todays_sacrifice = choice(everyone)
            user.send_message(
                "Today's sacrifice is @{}".format(todays_sacrifice)
            )
        else:
            user.send_message(
                "Nobody has offered themselves as a sacrifice."
            )

# Registering Commands----------------------------------------------------------
module_tools.register_command(main_regex, sacrifice, "moderator")
module_tools.register_command(reset_regex, sacrifice_reset, "moderator")
module_tools.register_command("sacrifices", sacrifice_count)
module_tools.register_command("sacrificeme", sacrifice_me,
                              cooldown=0, mod_cooldown=0)


