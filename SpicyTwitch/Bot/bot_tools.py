"""
Author: NekoGamiYuki
Version: 0.0.0

!!! STILL UNDER CONSTRUCTION !!!

Meant to be a module that manages all other commands.

Q: What is the concept behind the way SpicyB0t manages commands?
A: The way I see it, there's a chain of command when it comes to
   SpicyB0t, nothing extreme but it's how things currently work.
   It all starts at the main SpicyB0t application, where the user
   given by my Twitch API is sent over to the command manager.
   From there, based simply on the command a user gave, the Command
   Manager sends the user over to the corresponding command's
   manager. That manager then hands over the user to its "worker(s)"
   who do what is necessary for that specific bot feature.

   Example: The quote command (In this example the user does "!quote 2"
   - The twitch API gets a single line of chat, puts all that information
     into a variable known as the "user."
   - SpicyBot hands that user over to its Command Manager.
   - The Command Manager looks at its registered commands and chooses the
     appropriate Command Module. In this case, the "quotes" module.
   - The quotes module contains a local "quotes manager" that determines
     what the user intended to do.
   - The quotes manager finds that the user intends to read a quote and
     sends the user over to the "quote_read" worker.
   - The quote_read worker then looks at the necessary information and
     determines what it should do. One of the following:
        - It finds that the user attempted to access a deleted quote.
          Then it notifies the user about the deleted quote and when it
          was deleted.
        - It finds the quote, formats it, and sends it over to the
          channel the user chatted from.
"""

# TODO: Move timers to a seperate system?
"""
GOAL: Have a single set of functions to do the following:

- 4 categories for systems:
    - response : Will respond to user based on input
    - one-way : Simply takes input, does not respond
    - timer : Called after a certain amount of time passes.
    - moderation : Filters input

- add custom commands
- add general commands (the response type of command)
- delete general commands
- turn off custom commands
- have bot managers that get extra privileges
- Allow commands to register configuraiton variables that they use, so that
  the main command manager to configure them.
- Manage verbose output and logging of categories
- Manage configuration for each channel. (Global dictionary on this module)
- Maybe have a system for managing cooldowns? Like a simple class with mark() and check() methods.
"""

# TODO: Make it so main manager can have an option for asyncronous command launching.
#       In other words, it'll copy the user into a variable and pass it to a command.
#       Then, it'll simply ignore whether or not the command executed properly and
#       will exit, returning control to the main bot.

# TODO: Create a main storage pool for all commands to use and access easily via
#       a function. Make it specific to the OS/Kernel. Windows: Documents, Mac OS: Documents,
#       Linux: .config/

# TODO: Allow a command to register itself as "default" if the bot Allows it, that way someone
#       can create a bot that does something like
# TODO: Currently logging is limited to only the time, level, and message. This is because the
#       module_tools has functions that call the logger for a module from the dictionary of loggers.
#       This is problematic as it makes it so that logging is rather useless for tracing back issues!
#       I need to read up on python after I finish getting the system to its most basic, functioning,
#       state.
# Imported Modules -------------------------------------------------------------
import time
import logging
import os
from logging import NullHandler
import twitch
from . import module_tools
from .module_tools import DEFAULT_COMMAND_PREFIX


# Command Management -----------------------------------------------------------
def manage_user_input(user: twitch.User):

    module_tools.update_modules_for_new_channel(user.chatted_from)

    # NOTE: No commands should manipulate the user variable.
    if not module_tools.moderation_check(user):
        return False
    else:
        if DEFAULT_COMMAND_PREFIX in user.command[0]:
            # Manager does not care if these succeed. Maybe it should?
            module_tools.manage_response_commands(user)
        module_tools.hand_over_to_one_ways(user)

    # Save all data for modules
    if time.time() - module_tools.LAST_SAVE > module_tools.SAVE_COOLDOWN:
        module_tools.save_all()
