"""
Author: NekoGamiYuki
Version: 1.0.0

Description:
A way to create and manage deaths during a game. Specifically made for quick
managing of deaths during livestreams.
"""

# Imported Modules--------------------------------------------------------------
import re
import twitch
import warnings
from . import module_tools

# TODO: Allow for switching games.
# TODO: Allow decrementing and incrementing by specific values
#       Mods could do !dg for death_game and then name it.

# Global Variables--------------------------------------------------------------
default_config = {
    'current_game': '',
    'nickname': ''
}

default_data = {
    'deaths': {}
}

# Regex-------------------------------------------------------------------------
deathcount_regex = re.compile(r"dc( \w+)?")
increment_regex = re.compile(r"d( \d+)?")
decrement_regex = re.compile(r"dd( \d+)?")
add_game_regex = re.compile(r"deathcount add game (\w+|\W+)")
remove_game_regex = re.compile(r"deathcount remove (\w+|\W+)")
set_game_regex = re.compile(r"deathcount set game (\w+|\W+)")


# Module Registration-----------------------------------------------------------
module_tools.register_module(default_data, default_config)
logger = module_tools.create_logger()


# Safety checks-----------------------------------------------------------------


# Command functions ------------------------------------------------------------
def increment_deaths(user: twitch.User):

    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = increment_regex.findall(user_input)

    if parsed_input[0]:
        try:
            increment_by = int(parsed_input[0].strip())
        except ValueError:
            # I doubt this will ever launch, but I'd prefer not to have the bot
            # crash.
            logger.warning(
                "Failed to convert user's input into an integer! "
                "User input: {}".format(user.message)
            )
            return
    else:
        increment_by = 1

    data = module_tools.get_data(user.chatted_from)
    config = module_tools.get_config(user.chatted_from)

    game = config['current_game']

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod"
            "can set the game by using '!deathcount set game <game>'"
        )

    try:
        data['deaths'][game] += increment_by

        module_tools.update_data(user.chatted_from, data)

        logger.info(
            "Incremented death count by {} for channel "
            "{}.".format(increment_by, user.chatted_from)
        )

        user.send_message(
            "Death count has been incremented by {}, for the "
            "game '{}'. RIP sfhSAD".format(increment_by, config['current_game'])
        )
    except KeyError:
        # TODO: Log issue with current game. Although I don't think this will
        # happen because I'll create a command for setting the game
        pass
    except ValueError:
        user.send_message(
            "The death counter is broken! NotLikeThis. It seems to have been "
            "tampered with, as the counter is no longer a number! If you'd like"
            " to fix this quickly, you can have the streamer do !death_reset to"
            " reset the counter to Zero. Please have the admin of this bot look"
            " into this issue!")

        logger.critical(
            "Deaths for the game '{}' are set to something other than an"
            "integer. Did someone tamper with the save file?"
            "".format(config['current_game'])
        )


def decrement_deaths(user: twitch.User):
    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = decrement_regex.findall(user_input)

    if parsed_input[0]:
        try:
            decrement_by = int(parsed_input[0].strip())
        except ValueError:
            # I doubt this will ever launch, but I'd prefer not to have the bot
            # crash.
            logger.warning(
                "Failed to convert user's input into an integer! "
                "User input: {}".format(user.message)
            )
            return
    else:
        decrement_by = 1

    data = module_tools.get_data(user.chatted_from)
    config = module_tools.get_config(user.chatted_from)

    game = config['current_game']

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod"
            "can set the game by using '!deathcount set game <game>'"
        )


    try:
        if decrement_by > data['deaths'][game]:
            user.send_message("Nice try, but I won't let you get into the "
                              "negatives! sfhMAD")
            return
        else:
            data['deaths'][game] -= decrement_by

            logger.info(
                              "Decremented death count for channel "
                              "{}.".format(user.chatted_from)
            )

        streamer = user.chatted_from
        if config["nickname"]:
            streamer = config["nickname"]

        user.send_message(
            "Death count has been decremented by {} for the game {}. "
            "sfhOH {} lives!".format(
                decrement_by, config["current_game"], streamer
            )
        )
    except KeyError:
        # TODO: Log issue with current game. Although I don't think this will
        # happen because I'll create a command for setting the game
        pass
    except ValueError:
        user.send_message(
            "The death counter is broken! NotLikeThis. It seems to have been "
            "tampered with, as the counter is no longer a number! If you'd like"
            " to fix this quickly, you can have the streamer do !death_reset to"
            " reset the counter to Zero. Please have the admin of this bot look"
            " into this issue!")

        logger.critical(
            "Deaths for the game '{}' are set to something other than an"
            "integer. Did someone tamper with the save file?"
            "".format(config['current_game'])
        )


def reset_deaths(user: twitch.User):
    data = module_tools.get_data(user.chatted_from)
    config = module_tools.get_config(user.chatted_from)

    game = config["current_game"]

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod"
            "can set the game by using '!deathcount set game <game>'"
        )

    try:
        data['deaths'][game] = 0

        logger.info(
                              "Reset death count for channel "
                              "{}.".format(user.chatted_from)
        )

        user.send_message(
            "Deaths have been reset to zero for the game '{}'. "
            "sfhWOW".format(config["current_game"])
        )
    except KeyError:
        # TODO: Log issue with current game. Although I don't think this will
        # happen because I'll create a command for setting the game
        pass


def death_count(user: twitch.User):
    user_input = user.message.split(module_tools.DEFAULT_COMMAND_PREFIX, 1)[1]
    parsed_input = deathcount_regex.findall(user_input)

    config = module_tools.get_config(user.chatted_from)

    if parsed_input[0]:
        game = parsed_input[0].strip().lower()
    else:
        game = config["current_game"]

    if not game:
        user.send_message(
            "No game has been set for the death counter. The streamer or a mod "
            "can set the game by using '!deathcount set game <game>'"
        )
        return

    data = module_tools.get_data(user.chatted_from)

    try:
        deaths = data['deaths'][game]

        streamer = user.chatted_from
        if config["nickname"]:
            streamer = config["nickname"]

        if deaths > 1:
            user.send_message(
                "{} has died {} times. RIP sfhSAD".format(streamer, deaths)
            )
        elif deaths == 1:
            user.send_message("{} has died 1 time. RIP sfhSAD".format(streamer))
        elif deaths == 0:
            user.send_message("{} has yet to die! sfhOH".format(streamer))

        logger.info(
            "Read death count of {} for the game {}, in the channel "
            "{}. Incremented by {}.".format(
                deaths, game, user.chatted_from, user.name
            )
        )

    except KeyError:
        user.send_message("There is no death count for the game '{}' "
                          "sfhSHRUG".format(game))
    except ValueError:
        user.send_message(
            "The death counter is broken! NotLikeThis. It seems to have been "
            "tampered with, as the counter is no longer a number! If you'd like"
            " to fix this quickly, you can have the streamer do !death_reset to"
            " reset the counter to Zero. Please have the admin of this bot look"
            " into this issue!")

        logger.critical(
            "Deaths for the game '{}' are set to something other than an"
            "integer. Did someone tamper with the save file?"
            "".format(config['current_game'])
        )


def add_game(user: twitch.User):
    game = add_game_regex.findall(user.message)[0]

    data = module_tools.get_data(user.chatted_from)
    game_list = data['deaths'].keys()

    if game.lower() in game_list:
        user.send_message("{} is already in the list of games.".format(game))
    else:
        data['deaths'][game.lower()] = 0
        user.send_message("{} is now in the list of games! sfhOH".format(game))

        module_tools.update_data(user.chatted_from, data)


def set_game(user: twitch.User):
    game = set_game_regex.findall(user.message)[0]

    data = module_tools.get_data(user.chatted_from)
    config = module_tools.get_config(user.chatted_from)

    game_list = data['deaths'].keys()

    if game.lower() not in game_list:
        user.send_message(
            "{} is not in the list of games. If you'd like to add it to the "
            "list of games (and are a moderator), run '{}deaths add game {}'."
            "".format(game, module_tools.DEFAULT_COMMAND_PREFIX, game)
        )
    else:
        config["current_game"] = game.lower()
        module_tools.update_config(user.chatted_from, config)
        user.send_message("Game has been changed to {}. sfhOH".format(game))


def remove_game(user: twitch.User):
    game = remove_game_regex.findall(user.message)[0]

    data = module_tools.get_data(user.chatted_from)
    game_list = data['deaths'].keys()

    if game.lower() in game_list:
        del data['deaths'][game.lower()]
        user.send_message("{} has been removed from the list of games! "
                          "RIP".format(game))

        module_tools.update_data(user.chatted_from, data)
    else:
        user.send_message("{} is not in the list of games.".format(game))


# Registering Commands----------------------------------------------------------
module_tools.register_command("d( \d+)?", increment_deaths, "moderator")
module_tools.register_command("dd( \d+)?", decrement_deaths, "moderator")
module_tools.register_command("deathcount remove game (\w+|\W+)", remove_game, "moderator")
module_tools.register_command("deathcount add game (\w+|\W+)", add_game, "moderator")
module_tools.register_command("deathcount set game (\w+|\W+)", set_game, "moderator")
module_tools.register_command("dc( \w+)?", death_count)
module_tools.register_command("death_reset", reset_deaths, "broadcaster")

