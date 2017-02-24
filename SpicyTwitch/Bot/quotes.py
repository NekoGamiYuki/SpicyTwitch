"""
Author: NekoGamiYuki
Version: 1.0.0

Description:
A way to create and manage quotes. Specifically made for quick creation of
quotes during livestreams.
"""

# TODO: New goal is to make every command-function a "worker" that manages the twitch user.

# TODO: Create an update function that goes through the quote file and updates quotes using the previous Broadcaster
#       nickname to the new nickname. This can be done simply by comparing each line to the previous nickname and
#       changing all that match.
# TODO: After completing the necessary parts of the quote functionality, read up "Fluent Python"
# TODO: Add documentation to all functions.
# TODO: make it so that boolean functions return strings instead, so that chat
#       knows how much I fucked up with the bot.
# TODO: Implement configuration. Things like setting the broadascter nickname, cooldowns, etc.
# TODO: Consider changing certain function returns to int values that represent specific issues. (Maybe not)
# TODO: Use Emote class feature to find out whether emotes are at the start or end of a quote. Add appropriate spacing
#       to allow the emote to show.
# TODO: Maybe make a statistics value that shows how many times a quote is used (excluding random appears?).
# TODO: Consider making a help function, which states how to do some things... maybe...
# TODO: Log who creates/deletes/edits a quote and maybe the changes they made?
# TODO: ^ If done, consider creating a "revert/undo" function to revert a quote to its previous version. Also log that.
#       Have the revert function work both ways. If used on a reverted quote it'll return to the latest edit.
# TODO: Create a Quote class for more readability in code and easier management. Also would allow Quotes to be managed
#       by other command modules.
# TODO: Make broadcaster_nickname changes apply to the quotes file
# TODO: Section off specific parts of the bot, such as all the parts that have to do with reading, and all the parts
#       that have to do with writing. Give each of those a cooldown if necessary, so as to not have to use some global
#       cooldown. Maybe just give each function a cooldown.
# TODO: When fixing up the entire set of code, consider implementing a system to stop quotes for being repeated for some
#       time.
# TODO: With new command system, seperate !quotes and !quote cooldowns


# TODO: For the new system, how can I seperate things like read/edit/add !?
#       They should each have their own cooldown, but with the current way I'm
#       doing things, they'd all have the same cooldown because of the command
#       being registered running through quote_management.
#       Should I give the system the ability to use regex given by modules to
#       check whether or not a specific command is being used?

# Imported Modules--------------------------------------------------------------
import re
import datetime
from random import randint
from difflib import SequenceMatcher
import twitch
from . import module_tools

# Global Variables--------------------------------------------------------------
DELETED_FILL = "###DELETED###"

# Offset to account for spaces and any other extra characters when formatting
# the quote, so that it doesn't exceed twitch's character limit.
SIZE_OFFSET = 20

# Max size of a message
MAX_SIZE = 500

default_config = {
    "broadcaster_nickname": "YOURNICKNAMEHERE",
    "count_cooldown": "15",
    "read_cooldown": "15",
    "random_read_cooldown": "15",
}

default_data = {"quotes": []}

# Regex-------------------------------------------------------------------------
quote_read_regex = re.compile(r"quote( \d+)?")
quote_edit_regex = re.compile(r"quote edit (\d+) (-\w+=\w+)? (\w+)")
quote_add_regex = re.compile(r"quote add (-\w+=\w+)? (\w+)")
quote_delete_regex = re.compile(r"quote delete (\d+)")
# Module Registration-----------------------------------------------------------
MODULE_NAME = "Quotes"
module_tools.register_module(MODULE_NAME, "response", default_data, default_config)
module_tools.register_logger(MODULE_NAME, __name__)


# Transferring old quotes to new system
def transfer_quotes():
    pass

# TODO: Implement similarity tests.
# NOTE: I can see this maybe getting annoying so it should be possible to toggle.
# NOTE: We could respond with something like:
#       "That quote is rather similar to quote #{} sfhHM ... Maybe you should
#       take a look?"
#       But still make the quote, just in case.
"""
def _quote_similarity(channel_name: str, quote_text: str) -> str:
    if channel_quotes[channel_name]:
        similarity = []
        for quote in channel_quotes[channel_name]:
            similarity.append(SequenceMatcher(None, quote[0], quote_text).ratio())

        similarity_index, highest_similarity = max(enumerate(similarity), key=operator.itemgetter(1))
        if highest_similarity == 1.0:
            return "FeelsBadMan looks like your quote is already in the system. Check quote #{}".format(similarity_index)
"""


# TODO: Make counter state how many are deleted
# NOTE: Maybe make a function that runs when "!quotes deleted" is called?
# NOTE: Maybe have separate posts? One for cases where quotes have been deleted, another for when none are deleted?
def quote_count(user: twitch.User):

    quotes = module_tools.get_data(MODULE_NAME, user.chatted_from)['quotes']

    if quotes:
        # Getting number of quotes
        quote_count = len(quotes)

        # Getting number of deleted quotes
        deleted_count = 0
        for quote in quotes:
            if quote[0] == "###DELETED###" and quote[1] == "###DELETED###":
                deleted_count += 1

        print("Deleted Count: {}".format(deleted_count))
        if quote_count - deleted_count == 0:
            if quote_count > 1:
                twitch.chat("WutFace There are only deleted quotes, "
                            "{} of them! WutFace".format(deleted_count),
                            user.chatted_from)
            elif quote_count == 1:
                twitch.chat("WutFace There is only one quote and it was "
                            "deleted! WutFace", user.chatted_from)

        if quote_count > 150:
            twitch.chat(" NotLikeThis There are {} quotes and {} "
                        "are deleted! Will they ever stop!? "
                        "NotLikeThis".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count > 100:
            twitch.chat("\m/ SwiftRage \m/ {} quotes, {} were "
                        "burned at the stake! FUCK YEAH! "
                        "\m/ SwiftRage \m/".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count > 50:
            twitch.chat("PogChamp there are {} quotes and {}"
                        " of those were deleted! "
                        "PogChamp".format(quote_count, deleted_count),
                        user.chatted_from)
        elif quote_count == 1:
            twitch.chat("FeelsGoodMan there is 1 quote. FeelsGoodMan",
                         user.chatted_from)
        else:
            if deleted_count == 1:
                deleted_message = "1 was deleted!"
            else:
                deleted_message = "{} were deleted".format(deleted_count)
            twitch.chat("FeelsGoodMan there are {} quotes, of which {} "
                        "FeelsGoodMan".format(quote_count, deleted_message),
                        user.chatted_from)
    else:
        twitch.chat("FeelsBadMan there are no quotes. "
                    "FeelsGoodMan time to make some quotes!",
                    user.chatted_from)


def quote_read(user: twitch.User):

    parsed_input = quote_read_regex.findall(user.message)
    quotes = module_tools.get_data(MODULE_NAME, user.chatted_from)['quotes']

    if len(parsed_input) == 1:
        quote_number = randint(0, len(quotes))
        random = True
    else:
        random = False
        try:
            quote_number = int(parsed_input[1].strip()) - 1
        except ValueError:
            user.send_message("sfhWUT Not even sure what you're trying to do.")
            return

    if quote_number >= 0:

        try:
            quote_text = "\" {} \"".format(quotes[quote_number][0])
            broadcaster_name = quotes[quote_number][1].strip()

            config = module_tools.get_config(MODULE_NAME, user.chatted_from)

            # Use the new set nickname for the quote
            if config["broadcaster_nickname"] != default_config["broadcaster_nickname"]:
                if broadcaster_name.lower() == user.chatted_from:
                    broadcaster_name = config["broadcaster_nickname"]

            quote_date = str(quotes[quote_number][quote_number][-1])

            if quote_text == "\" ###DELETED### \"" and broadcaster_name == "###DELETED###" :
                if random:
                    index = quote_number
                    while quote_text == "\" ###DELETED### \"" and broadcaster_name == "###DELETED###":
                        index = randint(0, len(quotes))
                        if index > 0:
                            index -= 1
                        quote_text = "\" {} \"".format(quotes[index][0])
                        broadcaster_name = quotes[index][1].strip()

                        quote_date = "({})".format(quotes[quote_number][index][2])

                    # Use the new set nickname for the quote
                    if config["broadcaster_nickname"] != default_config["broadcaster_nickname"]:
                        if broadcaster_name.lower() == user.chatted_from:
                            broadcaster_name = config["broadcaster_nickname"]

                    quote_index = "[#{}]".format(index + 1)
                    quote = "{} - {} {} {}".format(
                        quote_text, broadcaster_name, quote_date, quote_index
                    )

                    twitch.chat(quote, user.chatted_from)
                else:
                    user.send_message("Quote #{} was deleted on {}. "
                                      "sfhSAD".format(quote_number + 1, quote_date))
            else:
                if random:
                    quote_index = "[#{}]".format(quote_number + 1)
                else:
                    quote_index = ''

                quote = "{} - {} {} {}".format(
                    quote_text, broadcaster_name, quote_date, quote_index
                )

                twitch.chat(quote, user.chatted_from)
        except IndexError:
            twitch.chat("Quote #{} does not exist. "
                        "FeelsBadMan".format(quote_number + 1),
                        user.chatted_from)

    # NOTE: I think the regex will stop this from ever happening, maybe I'll
    #       add a negative sign, allowing it to get negative numbers,
    #       just to liven up the bot a bit :)
    elif quote_number < 0:
        user.send_message("DansGame trying to get a quote from "
                          "before quotes were even a thing. Shame...")


# TODO: I think my use of the "too_large" variable makes it so that the original quote is not re-written to the file.
#       This causes it to be deleted, which is not what the _quote_edit() function should be doing...
def quote_edit(user: twitch.User):
    parsed_input = quote_edit_regex.findall(user.message)

    broadcaster_nickname = user.chatted_from
    if not len(parsed_input) >= 3:
        config = module_tools.get_config(MODULE_NAME, user.chatted_from)
        set_nickname = config['broadcaster_nickname']

        if not set_nickname == default_config['broadcaster_nickname']:
            broadcaster_nickname = set_nickname

    try:
        index = int(parsed_input[0])

        # Account for Zero-based indexing
        if index >= 1:
            index -= 1

    except ValueError: # This shouldn't ever be triggered, but... Gotta be safe.
        return  # NOTE: Maybe log something?

    # Get our module data from module_tools
    data = module_tools.get_data(MODULE_NAME, user.chatted_from)

    quoted_person = data['quotes'][index][1]
    date = data['quotes'][index][-1]
    quote_text = parsed_input.pop()

    for option in parsed_input:
        if '-name=' in option:
            try:
                broadcaster_nickname = option.split('=', 1)[1]
            except IndexError:
                # TODO: Log issue with option being wrong
                break  # NOTE Remember to remove this if I add more options!

    was_deleted = False
    # Check if the quote was previously deleted
    if quoted_person == DELETED_FILL:
        was_deleted = True
        # Update with a new name for the person being quoted
        quoted_person = broadcaster_nickname

        # Update the date, as this is a new quote
        date = datetime.datetime.now().date()

    if len(quote_text) + len(quoted_person) + len(str(date)) + SIZE_OFFSET > MAX_SIZE:
        user.send_message("Your quote was too large, please shorten it! sfhMAD")
    else:
        # Updated to the new quote
        data['quotes'][index][0] = quote_text
        data['quotes'][index][1] = quoted_person
        data['quotes'][index][-1] = date

        # Update module_tools to hold our newest set of data.
        module_tools.update_data(MODULE_NAME, user.chatted_from, data)

        if was_deleted:
            message = "Previously deleted quote has been reborn as a new " \
                      "quote! FeelsAmazingMan"
        else:
            message = "Quote #{} has been successfully edited! " \
                      "FeelsGoodMan".format(index + 1)

        user.send_message(message)


# TODO: WHen new system is implemented. Use twitch.user.emotes[] and find the start and end of each emote. If one
#       starts at 0 or ends at the very last character of the quote, add a space to the left or right respectively.
def quote_add(user: twitch.User):

    parsed_input = quote_add_regex.findall(user.message)

    # Set the new quote
    new_quote = parsed_input.pop()

    # Set the date
    quote_date = datetime.datetime.now().date()

    # Set default quoted person to the streamer's username.
    quoted_person = user.chatted_from

    # Check if user input a different name for the quoted person.
    for option in parsed_input:
        if '-name=' in option:
            try:
                quoted_person = option.split('=', 1)[1]
            except IndexError:
                pass

    else:  # If not, check if the broadcaster_nickname option has been set
        config = module_tools.get_config(MODULE_NAME, user.chatted_from)
        set_nickname = config['broadcaster_nickname']

        if not set_nickname == default_config['broadcaster_nickname']:
            quoted_person = set_nickname

    # Checking if new quote is too large
    if len(new_quote) + len(quoted_person) + len(str(quote_date)) + SIZE_OFFSET > MAX_SIZE:
        user.send_message("Your new quote was too large, please shorten it! "
                          "sfhMAD")
        return

    # Get the data stored by module_tools
    data = module_tools.get_data(MODULE_NAME, user.chatted_from)

    # Get our quotes from the stored data.
    quotes = data['quotes']

    # Check if that quote was already made before.
    for index, quote in enumerate(quotes):
        if new_quote.strip().lower() == quote[0].strip().lower():
            user.send_message("That quote is the same as quote #{}! "
                              "sfhPLS".format(index + 1))
            return

    # Pack the new quote into a list.
    quotes.append([new_quote, quoted_person, quote_date])

    # Update data that module_tools stores.
    data['quotes'] = quotes
    module_tools.update_data(MODULE_NAME, user.chatted_from, data)

    user.send_message("Quote #{} has been created! sfhWOW".format(len(quotes)))


def quote_delete(user: twitch.User):
    parsed_input = quote_delete_regex.findall(user.message)

    if not parsed_input:
        user.send_message("Which quote would you like to delete. Or do you "
                          "want me to guess? GIGALUL")
    else:
        index = int(parsed_input[0]) - 1

        data = module_tools.get_data(MODULE_NAME, user.chatted_from)
        quotes = data['quotes']

        try:
            if quotes[index][0] == DELETED_FILL and quotes[index][1] == DELETED_FILL:
                user.send_message("Quote #{} was already deleted on {}. "
                                  "sfhHM".format(index + 1, quotes[index][-1]))

            quotes[index] = [DELETED_FILL,  # Set the quote text as deleted
                             DELETED_FILL,  # Set the quoted person as deleted
                             datetime.datetime.now().date()  # Set deletion date
                             ]
        except IndexError:
            user.send_message("Quote #{} does not exist "
                              "sfhSHRUG".format(index + 1))


module_tools.register_command(MODULE_NAME, r'quotes', quote_count)
module_tools.register_command(MODULE_NAME, r'quote( \d+)?', quote_read)
module_tools.register_command(MODULE_NAME, r'quote add \w+', quote_add, "moderator")
module_tools.register_command(MODULE_NAME, r'quote edit', quote_edit, "moderator")
module_tools.register_command(MODULE_NAME, r'quote delete \d+', quote_delete, "moderator")
