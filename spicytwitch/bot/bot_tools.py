# NOTE: One issue I can see happening is that checking timers on each call of
#       manage_timer_modules() is limited by how often the bot or this module
#       call the function itself. So even though a timer might be set to run
#       every 30 seconds, the function might not be called until a couple 
#       minutes have passed! For that reason, I think I should look into
#       threading so as to seperate the timer process as something that is
#       automatically ran on startup. The timers can simply check a global var
#       so as to see whether or not they are enabled, or even easier would be
#       to have the manage_timer_modules() just be the function that is ran as
#       a thread!


# Imports-----------------------------------------------------------------------
from .. import irc
from . import modules


# Command Managers--------------------------------------------------------------
def manage_response_modules(user: irc.User):
    for module in modules.RESPONSE_MODULES.values():
        user_copy = user
        if module.run_command(user_copy):
            # If we run a command, break as we don't need to continue trying to
            # run any other commands.
            break
        

def manage_moderation_modules(user: irc.User) -> bool:
    for module in modules.MODERATION_MODULES.values():
        user_copy = user
        if not module.check(user_copy):
            return False

    # If we go through each moderation module and everything checks out.
    return True


def manage_timer_modules():
    pass

def manage_all_modules(user: irc.User):

    user_copy = user
    if manage_moderation_modules(user_copy):
        manage_response_modules(user_copy)

    # Always making sure to check the timers
    manage_timer_modules()


# Cleanup functions-------------------------------------------------------------
def run_cleanup():
    for function in modules.SHUTDOWN_FUNCTIONS:
        function()
