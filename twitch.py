"""
Author: NekoGamiYuki
Version: 0.2.7

Description:
A simple twitch API. Current version will be rather basic, with the main ability
being that it is capable of reading twitch chat.

Examples:
Example program is located in the 'Examples' folder.
"""

# TODO: Add logging capabilities (maybe)
# TODO: Update all print/string statements to use .format instead of %
# TODO: Finish adding docstrings and commenting out code
# TODO: Make get_info check for CAP NACK.
# TODO: Make manage_irc capable of basic IRC if tags aren't ACK'd
# TODO: With new regex I can check if the bot is a mod! I could create a 'me'
#       class and check channels I have joined for my status within them.
# TODO: If desired, I could put all of this into a class. That would make this
#       module capable of managing multiple bots. Though I find that unnecessary,
#       but cool.
# TODO: Add local time to User class.
# TODO: twitchnotifty is the user that notifies everyone of new subscribers
# TODO: Need to implement the select module as soon as possible~!
# TODO: Consider merging SpicyTwitchIRC and SpicyBotAPI into SpicyTwitch.bot
#       and Spicytwitch.irc respectively, as a single package.
# TODO: Either turn this into a class or create a class using this module. This
#       will allow for the use of multiple users, which will be useful for certain
#       applications that might want to allow multi-user applications

# TODO: Rewrite returns of all functions to take advantage of raising exceptions
# I want to make it so that I raise exceptions instead of just returning False.
# Things like not giving me a username when connecting are VERY serious, and
# therefore require an exception, a complete stop, rather than a return value.

# NOTE: Turns out you can actually PING twitch... The same way I send a PONG,
# but replace it with PING. They reply with a PONG. This is what I was doing
# accidentally this entire time...

# Imported Modules--------------------------------------------------------------
import warnings
import logging
from logging import NullHandler
import socket
import time
import re
import os

# Global Variables--------------------------------------------------------------
_SOCK = None
_TWITCH = "irc.chat.twitch.tv"  # Compliant with twitch's new server
_PORT = 6667  # Not using twitch's SSL capable server's

# Connection information
_CONNECTION_PROTOCOL = ''  # Do not set this yourself! Use connect() instead
_RECONNECT = False
is_connected = False

# Configuration variables for _send_info()
_commands_sent = 0
_send_time = 0
_RATE = 100  # No more than 100 commands sent every 30 seconds

# User information (for reconnecting)
_username = ''
_oauth = ''  # Good idea? It's the only way I know of keeping it around...

# Twitch chat information
channels = {}
notification = {}  # Holds a single notification from twitch (channel_name, message)
user = None  # Once initialized by get_info() it contains a single users info

# Logging
irc_logger = logging.getLogger(__name__)
logging.basicConfig(format='[%(asctime)s] [%(levelname)s] [%(module)s] (%(funcName)s): %(message)s',
                    datefmt='%Y/%m/%d %I:%M:%S %p')

# Regular Expressions-----------------------------------------------------------
# TODO: do a re.match for each of these to test which parser to send the information to?
# TODO: Maybe add r"$" to the end of each of these?
# For capturing ACK/NAK from capability requests.
cap_regex = re.compile(r"^:tmi\.twitch\.tv CAP \* ([A-Z]+) :twitch\.tv/(\w+)")
# Gets badges, a number and space (unknown why it does that...),
# extra information, COMMAND, channel, and message if available.
tags_regex = re.compile(r"^@((\w|\W)+):(\w+!\w+@\w+\.)?tmi\.twitch\.tv ([A-Z]+) #(\w+)[ ]?:?([\S\s]+)?")
# Gets username, extra information, channel, and user's message.
irc_chat_regex = re.compile(r"^:(\w+)!(\w+@\w+\.tmi\.twitch\.tv) ([A-Z]+) #(\w+) :?([\S\s]+)?")
# Gets channel and string of all usernames.
# Although this says "start", I think twitch sends this for each list of users. So it can
# send multiple of these for the same channel until the list is done. I can use name_end for
# logging purposes as it really won't be useful for anything else.
names_start_regex = re.compile(r"^:\w+\.tmi\.twitch\.tv 353 \w+ = #(\w+) :([\S\s]+)")
# Gets channel
names_end_regex = re.compile(r"^:\w+\.tmi\.twitch\.tv 366 \w+ #(\w+) :([\S\s]+)")
# Gets channel and username
# NOTE: Sometimes is incomplete on channel name! Maybe do a check to see if the
#       partial channel name fits inside only ONE of the current channels? If more than
#       than one match, maybe discard? Or throw into an "unknown" bin.
join_part_regex = re.compile(r"^:(\w+)!(\w+@\w+\.tmi\.twitch\.tv) ([A-Z]+) #(\w+)")
mod_regex = re.compile(r"^:jtv ([A-Z]+) #(\w+) ([-+])o (\w+)")


# Logging-----------------------------------------------------------------------
def enable_logging(level=logging.INFO, log_to_file=False, file_path=''):
    # To print logs to the console/terminal.
    irc_logger.addHandler(NullHandler())

    # For saving logs to a file. Currently only saves to a single file. Considering making it save to
    # a new file based on the date, so as to not have an extremely large log file.
    if log_to_file:
        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_handler = logging.FileHandler(file_path)
        irc_logger.addHandler(file_handler)

    irc_logger.setLevel(level)


# Classes-----------------------------------------------------------------------
# TODO: Add followers_only check.
class Channel(object):
    """
    Contains information about a single channel. Such as their viewers, the
    message count (since you joined), whether they're in slow mode, etc...

    Information contained in class:
    name: Name of the channel
    moderators: Moderators of the channel, updated when a mod chats
    banned_users: All banned users since you joined, and any reasons for the ban
    timed_out_users: All users that have been timed out, and the seconds/reason.
    viewers: A list of all viewers.
    language: If a channel designated a language, it goes here.
    slow_mode: Whether the channel has slow mode on
    slow_time: The time for the slow mode cooldown
    r9k_mode: Whether the channel has r9kbeta on
    subscribers_only: Whether the channel has subscriber-mode on
    followers_only: Whether the channel has followers-mode on.
    hosting: Whether the channel is hosting
    hosted_channel: What channel is being hosted

    """

    def __init__(self, name: str):
        if name:
            self.name = name
        else:
            raise ValueError("Channel objects must have a non-empty name.")

        # How many messages were chatted since you joined
        self.message_count = 0
        self.moderators = []
        self.banned_users = {}
        self.timed_out_users = {}
        self.viewers = []
        self.language = ''
        self.slow_mode = False
        self.slow_time = 0
        self.r9k_mode = False
        self.subscribers_only = False
        self.followers_only = False
        self.hosting = False
        self.hosted_channel = ''


# TODO: If useful for future, add emote url and function for getting the image.
#       function should cache the image locally for multiple uses.
class Emote(object):
    """
    Contains information relating to an emote. The Name, ID, and position in
    a string are provided.

    Information you can get from this class:
    name: Name of the emote
    id: Id of the emote, for use in other parts of the twitch API (not this one)
    position: Start and End position of the emote in the user's message

    """

    def __init__(self, name: str, id_number: int, start: int, end: int):
        self.name = name
        self.id = id_number
        self.position = {"start": start, "end": end}


# TODO: Add purge capability
# TODO: Add unban and untimeout capabilities.
# TODO: Add reason to timeout()
class User(object):
    """
    Largest class in the API. Contains as much information about a user as given
    by Twitch.

    You can get their:
    name: Username
    message: What they just said in a channel (that you are joined to)
    chatted_from: What channel they just spoke from
    is_broadcaster: Whether they're a broadcaster
    is_mod: Whether they're a moderator
    is_sub: Whether they're a subscriber
    is_turbo: Whether they're a turbo subscriber
    user_type: This can be Admin, Staff, Mod, and anything else twitch adds
    color: The color of the user
    emotes: A collection of Emote objects, each relating to an emote the user
            used in chat.
    command: For bots, it's the first word in their message.

    Functions:
    ban(): Ban a user
    timeout(): Timeout a user
    purge(): Purge a user
    send_message(): Sends/Directs a message to a user in chat
    """

    # TODO: Consider renaming "extra" to something more specific.
    def __init__(self, extracted_tag_data: dict, channel_chatted_from: str,
                 chat_message: str, extra: str, filler_message="UNASSIGNED"):
        filler = filler_message  # For when we can't assign a value
        if not extracted_tag_data:
            self.name = filler
            self.message = filler
            self.chatted_from = filler
            self.is_broadcaster = False
            self.is_mod = False
            self.is_sub = False
            self.is_turbo = False
            self.user_type = filler
            self.color = filler
            self.emotes = []
            self.command = filler
        else:
            try:
                # Basic user information
                self.name = extracted_tag_data["display-name"]
                if not self.name:
                    self.name = extra.split('!')[0]

                self.message = chat_message
                # Where the user last chatted from
                self.chatted_from = channel_chatted_from

                # Role information
                if self.name.lower() == self.chatted_from:
                    self.is_broadcaster = True
                else:
                    self.is_broadcaster = False

                # ??? Double conversion because bool would see '0' as true
                self.is_mod = bool(int(extracted_tag_data["mod"]))
                self.is_sub = bool(int(extracted_tag_data["subscriber"]))
                self.is_turbo = bool(int(extracted_tag_data["turbo"]))

                # The user's role
                if extracted_tag_data["user-type"] is ' ':
                    self.user_type = filler
                else:
                    self.user_type = extracted_tag_data["user-type"] # Admin, Staff, Mod, etc...

                # Styling information
                if not extracted_tag_data["color"]:
                    self.color = filler
                else:
                    self.color = extracted_tag_data["color"]

                # NOTE: Twitch actually shows the months/bits for the badge a user has. I just
                #       saw someone talked that had "subscriber/6" and "bits/10000", then checked
                #       twitch chat and it showed them with a 6 month sub badge and a cheer 10000
                #       badge!
                self.badges = {}
                if extracted_tag_data["badges"]:
                    for badge in extracted_tag_data["badges"].split(','):
                        data = badge.split('/')
                        # TODO: Convert data[1] to int?
                        self.badges[data[0]] = data[1]

                # Emotes!
                self.emotes = []
                if extracted_tag_data["emotes"]:
                    for info in extracted_tag_data["emotes"].split('/'):
                        for position in info.split(":")[1].split(','):
                            start = int(position.split('-')[0])
                            end = int(position.split('-')[1]) + 1
                            name = self.message[start:end]
                            id = int(info.split(":")[0])
                            self.emotes.append(Emote(name,
                                                      id,
                                                      start,  # Start position
                                                      end))  # end position

                # Bot information (Useful for bots) It's the first word of their
                # chat message.
                self.command = self.message.split()[0]
            # TODO: Maybe change this?
            except (KeyError, TypeError) as error_information:
                error_filler = ("ERROR: Please check  user.error if this "
                                "issue persists.")
                self.name = error_filler
                self.message = error_filler
                self.message_history = []
                self.chatted_from = error_filler
                self.is_broadcaster = False
                self.is_mod = False
                self.is_sub = False
                self.is_turbo = False
                self.user_type = error_filler
                self.color = error_filler
                self.emotes = []
                self.command = error_filler
                self.error = error_information

    # NOTE: Would "reply" be a better name?
    def send_message(self, message: str, append_symbol=True) -> bool:
        """
        Send a message to this user. This is for chatting, not twitch messaging
        nor whispering. It pops up in chat as "@user <message>"

        Args:
            message: What you would like to tell the user
            append_symbol: Appends the '@' symbol at the start of the username

        Returns:
            True: When it succeeds in sending a message
            False: If it fails to send the message.

        """
        if not message:
            return False

        if append_symbol:
            formatted_message = "{}{} {}".format('@', self.name, message)
        else:
            formatted_message = "{} {}".format(self.name, message)

        if not chat(formatted_message, self.chatted_from):
            return False
        else:
            return True

    def purge(self, reason='') -> bool:
        """
        Purges (times out for 1 second) this user.

        Args:
            reason: The reason for the purging of this user

        Returns:
            True: When it succeeds to send the purge command
            False: When it fails to send the purge command

        """
        if self.timeout(1, reason):
            return True
        else:
            return False

    def timeout(self, seconds=600, reason='') -> bool:
        """
        Times out this user.

        Args:
            seconds: The duration of the timeout in seconds. Default 600.
            reason: The reason for timing out this user.

        Returns:
            True: When it succeeds in sending the timeout command to twitch
            False When it fails at sending the timeout command to twitch

        """
        # Doesn't matter if the reason is blank!
        if chat("/timeout {} {} {}".format(self.name, seconds, reason), self.chatted_from):
            return True
        else:
            return False

    def ban(self, reason='') -> bool:
        """
        Permanently Bans this user. Can be given a reason, which shows up in
        chat as a twitch notification.

        Args:
            reason: The reason for banning the user

        Returns:
            True: If it succeeds at sending the Ban command to twitch.
            False: if it fails at sending the Ban command to twitch.

        """
        # Doesn't matter if the reason is blank!
        if chat("/ban {} {}".format(self.name, reason), self.chatted_from):
            return True
        else:
            return False


# Parsing-----------------------------------------------------------------------
# TODO: Create functions for managing each command. Use _manage_tags to determine
#       which function to use.
# TODO: Manage GLOBALUSERSTATE, use to create a "me" variable that contains our
#       user's information.
def _manage_tags(input_data: str):
    """
    Manages most tags given by Twitch. Specifically, it manages PRIVMSG, NOTICE,
    ROOMSTATE, and CLEARCHAT tags. Updates the corresponding variables, such as
    updating the "user" variable when a new PRIVMSG is received (A single chat
    line).

    Updates the following variables:
    user: Is updated with the latest information from a single line of chat
    channels: Updates any information relating to the channel
    notification: Places the latest notification from chat, along with the
                  channel it came from
    Args:
        input_data: The data, from Twitch, that will be parsed.

    """

    if input_data:
        # At times twitch sends some broken/weird data, the one that caused
        # this one to break was '@user.tmi.twitch.tv PART #channel', since
        # JOIN/PARTS aren't meant to start with @, this was unexpected and
        # broke the parsing by being sent to the wrong parser.
        try:
            irc_logger.debug("Twitch Data: {}".format(input_data))
            twitch_data = tags_regex.findall(input_data)[0]
            irc_logger.debug("Parsed result: {}".format(twitch_data))  # DEBUG!!!
            extracted_tag_data = {}
            irc_logger.debug("Extracting data from tags.")
            for data in twitch_data[0].split(';'):
                extracted_tag_data[data.split('=')[0]] = data.split('=')[1]
            irc_logger.debug("Extracted tag data: {}".format(extracted_tag_data))
        except IndexError:
            warnings.warn("Received unexpected/broken data in _manage_tags(). Will not attempt to parse")
            return  # We will not try to parse broken/strange data.

        # TODO: Consider whether I should do USERSTATE or GLOBALUSERSTATE since
        # PRIVMSG has the same tags.
        global user
        global channels
        global notification

        # Time to parse the tags!
        if twitch_data[-3] == "PRIVMSG":  # Chat lines
            # Increment channel message count
            if twitch_data[-2] in channels:
                channels[twitch_data[-2]].message_count += 1

            # Update user variable
            irc_logger.info("Updating user variable.")
            user = User(extracted_tag_data, twitch_data[-2], twitch_data[-1], twitch_data[-4])

            # Sometimes this breaks, specifically when a user calls leave_channel()
            # as that deletes the channel from the channels dictionary.
            try:
                # Since we get to see if a user is a mod here, we add them to their
                # respective channel's moderator list if they're not already there.
                moderator_list = channels[user.chatted_from].moderators
                if user.is_mod and user.name.lower() not in moderator_list:
                    irc_logger.info("Adding {} to {}'s mod list.".format(user.name, user.chatted_from))
                    channels[user.chatted_from].moderators.append(user.name)
                elif not user.is_mod and not user.is_broadcaster and user.name.lower() in moderator_list:
                    irc_logger.info("Removing {} from {}'s mod list.".format(user.name, user.chatted_from))
                    channels[user.chatted_from].moderators.remove(user.name)

                # We can also add them to the list of viewers if they weren't
                # already there.
                viewers = channels[user.chatted_from].viewers
                if user.name and user.name.lower() not in viewers:
                    irc_logger.info("Adding {} to {}'s viewer list.".format(user.name.lower(), user.chatted_from))
                    channels[user.chatted_from].viewers.append(user.name.lower())
            except KeyError:
                irc_logger.error("Attempted to add user to a channel list that no longer exists. This is likely a "
                                 "result from leaving a channel while the module parsed a user's chat message. Nothing "
                                 "can be done about it, it should not affect your program.")
                pass

        elif twitch_data[-3] == "NOTICE":  # Twitch NOTICE tag management
            affected_channel = twitch_data[-2]
            message_id = twitch_data[0].split('=')[1].strip()

            notification["channel_name"] = affected_channel
            notification["message"] = twitch_data[-1]

            if "slow" in message_id:
                if "on" in message_id:
                    irc_logger.info("Marking slow mode as on for {}.".format(affected_channel))
                    channels[affected_channel].slow = True
                else:
                    irc_logger.info("Marking slow mode as off for {}.".format(affected_channel))
                    channels[affected_channel].slow = False
            elif "subs" in message_id:
                if "on" in message_id:
                    irc_logger.info("Marking subscriber mode as on for {}.".format(affected_channel))
                    channels[affected_channel].subscriber = True
                else:
                    irc_logger.info("Marking subscriber mode as off for {}.".format(affected_channel))
                    channels[affected_channel].subscriber = False
            elif "r9k" in message_id:
                if "on" in message_id:
                    irc_logger.info("Marking r9k mode as on for {}.".format(affected_channel))
                    channels[affected_channel].r9k = True
                else:
                    irc_logger.info("Marking r9k mode as off for {}.".format(affected_channel))
                    channels[affected_channel].r9k = False

            # TODO: NEED TO CHECK IF THIS STILL WORKS!
            elif "host" in message_id:
                if "on" in message_id:
                    hosted_channel = re.findall(r"Now hosting (\w+).", notification["message"])[0]
                    irc_logger.info("Marking host mode as on for {}.".format(affected_channel))
                    channels[affected_channel].hosting = True
                    irc_logger.info("Setting {} as hosted channel for {}.".format(
                        hosted_channel, affected_channel
                    ))
                    channels[affected_channel].hosted_channel = hosted_channel
                else:
                    irc_logger.info("Marking host mode as off and resetting hosted channel")
                    channels[affected_channel].hosting = False
                    channels[affected_channel].hosted_channel = ''

        elif twitch_data[-3] == "ROOMSTATE":
            affected_channel = twitch_data[-2]

            # TODO: Check for "followers-only"
            irc_logger.info("Getting channel ROOMSTATE (Basic information for when you first enter a channel).")
            if "broadcaster-lang" in extracted_tag_data.keys():
                if extracted_tag_data["broadcaster-lang"]:
                    irc_logger.info("Setting {}'s channel language as {}.".format(
                        affected_channel, extracted_tag_data["broadcaster-lang"]
                    ))
                    channels[affected_channel].language = extracted_tag_data["broadcaster-lang"]
                else:
                    irc_logger.warning("Channel {} has not set its language. This is ok in most cases.".format(affected_channel))
                    channels[affected_channel].language = ''
            elif "slow" in extracted_tag_data.keys():
                if extracted_tag_data["slow"] == '0':
                    irc_logger.info("Marking slow mode as off for {}.".format(affected_channel))
                    channels[affected_channel].slow_mode = False
                    channels[affected_channel].slow_time = 0
                    irc_logger.info("Slow time is set to 0 for {}.".format(affected_channel))

                else:
                    channels[affected_channel].slow_mode = True
                    channels[affected_channel].slow_time = int(extracted_tag_data["slow"])
                    irc_logger.info("Slow time is set to {} for {}.".format(
                        extracted_tag_data["slow"], affected_channel
                    ))
            elif "subs-only" in extracted_tag_data.keys():
                if '0' in extracted_tag_data["subs-only"]:
                    irc_logger.info("Marking subscriber mode as off for {}.".format(affected_channel))
                    channels[affected_channel].subscribers_only = False
                else:
                    irc_logger.info("Marking subscriber mode as on for {}.".format(affected_channel))
                    channels[affected_channel].subscribers_only = True
            elif "followers-only" in extracted_tag_data.keys():
                if '-1' in extracted_tag_data["followers-only"]:
                    irc_logger.info("Marking followers-only mode as off for {}.".format(affected_channel))
                    channels[affected_channel].followers_only = False
                else:
                    irc_logger.info("Marking followers-only mode as on for {}.".format(affected_channel))
                    channels[affected_channel].followers_only = True
            elif "r9k" in extracted_tag_data.keys():
                if '0' in extracted_tag_data["r9k"]:
                    irc_logger.info("Marking r9k mode as off for {}.".format(affected_channel))
                    channels[affected_channel].r9k_mode = False
                else:
                    irc_logger.info("Marking r9k mode as on for {}.".format(affected_channel))
                    channels[affected_channel].r9k_mode = True

        elif twitch_data[-3] == "CLEARCHAT":
            affected_channel = twitch_data[-2]
            affected_user = twitch_data[-1]

            # TODO: Check if ban duration exists. Else this crashes the module when
            #       someone is perma banned.
            # TODO: Make timed_out_users a dict so that both reason and duration can be added.
            # TODO: Also remove users after allotted amount of time. Or add time when user was
            #       timed out/banned.
            # TODO: Once updated ^ add logging calls as well.
            # With ban-duration, the user is timed out.
            if "ban-duration" in extracted_tag_data.keys():
                irc_logger.info("Added {} to timed out users in {}'s channel.".format(
                    affected_user, affected_channel
                ))
                channels[affected_channel].timed_out_users[affected_user] = {
                    "duration": extracted_tag_data["ban-duration"]
                }
                if "ban-reason" in extracted_tag_data.keys():
                    channels[affected_channel].timed_out_users[affected_user] = {
                        "reason": extracted_tag_data["ban-reason"]
                    }
            # WIth no ban-duration, the user is perma banned.
            elif "ban-reason" in extracted_tag_data.keys():
                irc_logger.info("Added {} to banned users in {}'s channel.".format(
                    affected_user, affected_channel
                ))
                channels[affected_channel].banned_users[affected_user] = {
                    "reason": extracted_tag_data["ban-reason"]
                }

            # TODO: Consider updating the notification var with timeout/ban info


# TODO: Implement regex for HOSTTARGET and manage RECONNECT calls.
# TODO: Manage CAP NAK
def _parse_irc(irc_info: str):
    """
    Parses any information that _manage_tags does not. This, for now, is just
    any JOINS and PARTS, as well as whenever hosting is started (however,
    hosting is also managed by _manage_tags, this mainly serves as a backup.).

    Args:
        irc_info: Any information from twitch that isn't a tag

    Returns:
        False: If it doesn't get information or Fails to parse.
        True: When it parses the information
    """

    # DEBUG !!!
    """
    print('-' * 80)
    print("cap: {}".format(cap_regex.findall(irc_info)))
    print("irc_chat: {}".format(irc_chat_regex.findall(irc_info)))
    print("join_part: {}".format(join_part_regex.findall(irc_info)))
    print("name_start: {}".format(names_start_regex.findall(irc_info)))
    print("name_end: {}".format(names_end_regex.findall(irc_info)))
    print("mod: {}".format(mod_regex.findall(irc_info)))
    """

    # This feels incredibly inefficient but it works...
    cap = cap_regex.findall(irc_info)
    irc_chat = irc_chat_regex.findall(irc_info)
    join_part = join_part_regex.findall(irc_info)
    mod_unmod = mod_regex.findall(irc_info)
    names_start = names_start_regex.findall(irc_info)

    global channels
    global notification

    # Managing commands
    if names_start:
        # Manage list of usernames/viewers given by twitch when you first
        # join a channel.
        names_affected_channel = names_start[0][0]
        name_list = names_start[0][1].split()
        irc_logger.info("Adding multiple usernames to {}'s viewers list.".format(names_affected_channel))
        for name in name_list:
            if name.lower() not in channels[names_affected_channel].viewers:
                channels[names_affected_channel].viewers.append(name.lower())
    elif join_part:
        username = join_part[0][0]
        affected_channel = join_part[0][-1]

        # Temp fix for incomplete channel names being given.
        # TODO: use SequenceMatcher from difflib module to get similarity of
        #       given channel name to names in channels dictionary. If more
        #       than, say, 75% similarity we'll use the channel.name.
        for channel in channels.keys():
            if join_part[0][-1] in channel:
                affected_channel = channel

        if join_part[0][-2] == "JOIN":
            if username not in channels[affected_channel].viewers:
                irc_logger.info("Adding {} to {}'s viewers list.".format(username, affected_channel))
                channels[affected_channel].viewers.append(username)
        elif join_part[0][-2] == "PART":
            if username in channels[affected_channel].viewers:
                irc_logger.info("Removing {} from {}'s viewer list.".format(username, affected_channel))
                channels[affected_channel].viewers.remove(username)

    elif mod_unmod:
        affected_user = mod_unmod[0][-1]
        affected_channel = mod_unmod[0][1]

        if mod_unmod[0][2] == '-':
            if affected_user.lower() in channels[affected_channel].moderators:
                for i, username in enumerate(channels[affected_channel].moderators):
                    if username == affected_user:
                        irc_logger.info("Removing {} from {}'s mod list.".format(affected_user, affected_channel))
                        del channels[affected_channel].moderators[i]
        elif mod_unmod[0][2] == '+':
            if affected_user.lower() not in channels[affected_channel].moderators:
                irc_logger.info("Adding {} to {}'s mod list.".format(affected_user, affected_channel))
                channels[affected_channel].moderators.append(affected_user.lower())
    elif cap:
        ack_nack = cap[0][0]
        request = cap[0][1]

        # TODO: Do something when memberships are acknowledged/denied
        if request == "membership":
            if ack_nack == "ACK":
                irc_logger.info("IRCv3 membership acknowledged by Twitch.")
            else:
                irc_logger.warning("IRCv3 membership denied by Twitch.")
        elif request == "commands":
            if ack_nack == "ACK":
                irc_logger.info("Commands request acknowledged by Twitch.")
            else:
                irc_logger.warning("Commands request denied by Twitch.")
        elif request == "tags":
            if ack_nack == "ACK":
                irc_logger.info("Tags request acknowledged by Twitch.")
            else:
                irc_logger.warning("Tags request denied by Twitch.")

    elif irc_chat:
        # TODO: Edit user variable(?)
        sender = irc_chat[0][0]
        affected_channel = irc_chat[0][-2]
        # TODO: Change name to something more generic?
        sub_resub_notification = irc_chat[0][-1]
        if sender == "twitchnotify":
            irc_logger.info("Updating notification dictionary.")
            notification["channel_name"] = affected_channel
            notification["message"] = sub_resub_notification


# Twitch Communication----------------------------------------------------------
# TODO: Actually increment the "commands_sent" variable.
def _send_info(info: str) -> bool:
    """
    This is the most used function within the API. It serves one purpose, to
    communicate directly with twitch. _send_info() takes one argument, "info",
    which is whatever you want to send to twitch's IRC servers. It is also the
    only function that uses the RAW_VERBOSE variable. If that variable is set
    to True, _send_info() will print out what it is sending to twitch. With the
    only exception being your OAUTH. Twitch receives your oauth via the
    following: "PASS oauth...\r\n", and _send_info() will not print or log your
    oauth for security reasons.

    Args:
        info: The information that will be sent to twitch

    Returns:
        True: If it is able to send the information
        False: If it is unable to send the information

    Raises:
        ValueError: If _CONNECTION_PROTOCOL is not 'tcp' or 'udp'

    """

    # TODO: Limit how often the program sends info
    # NOTE: Have it so that we check the list of mods on the channel a user is
    # messaging. If that user is part of the mods, then we allow them to send
    # up to 100 commands in 30 seconds. If they are not, we limit them to 30.
    # This will require keeping track of how many messages were sent by a user
    # to a specific channel and how much time has elapsed since the first one
    # was sent. After 30 seconds pass, we reset the message counter.

    global _commands_sent
    global _send_time

    time_elapsed = time.time() - _send_time

    if _CONNECTION_PROTOCOL is not "tcp" and _CONNECTION_PROTOCOL is not "udp":
        raise ValueError("_send_info() given connection protocol that was not"
                         " tcp nor udp.")
    else:
        if time_elapsed > 30:
            _commands_sent = 0
            _send_time = time.time()
        if _commands_sent < _RATE:

            total_sent = 0
            message = info.encode('utf-8')
            while total_sent < len(message):
                # ??? There's a chance that we might disconnect or have a hiccup
                try:
                    # NOTE: Do not loop in an attempt to resend possibly incomplete
                    # info as you will face the consequences... 2 hours of waiting
                    # here I come...
                    if _CONNECTION_PROTOCOL is "tcp":
                        sent = _SOCK.send(message[total_sent:])
                        if sent == 0:
                            raise RuntimeError("Socket connection broken.")
                        total_sent += sent
                    elif _CONNECTION_PROTOCOL is "udp":
                        sent = _SOCK.sendto(message[total_sent:], (_TWITCH, _PORT))

                        if sent == 0:
                            raise RuntimeError("Socket connection broken.")
                        total_sent += sent
                except InterruptedError:
                    return False
            irc_logger.debug("Sent data using {}. Total amount sent: {}".format(_CONNECTION_PROTOCOL, total_sent))
            return True


# Twitch Interaction------------------------------------------------------------
def chat(message: str, channel: str) -> bool:
    """
    Sends a chat message to a specific channel.

    Args:
        message: What you would like to send to the channel's chat
        channel: The channel you'd like to send the message to

    Returns:
        True: When it sends the message
        False: if it is given an empty string or is unable to send the message
    """
    if not message:
        warnings.warn("chat() was not given a message to send. Instead received an empty string.")
        return False
    elif not channel:
        warnings.warn("chat() was not given a channel to send the message to.")
        return False
    else:
        irc_logger.info("Sending chat message to channel {}".format(channel))
        if not _send_info("PRIVMSG #{} :{}\r\n".format(channel, message)):
            return False
        else:
            return True


def join_channel(channel: str, rejoin=False) -> bool:
    """
    Joins a channel's chat, allowing the API to receive information from that
    channel. Updates the channels variable with a new channel object, named
    after the channel you've joined.

    Args:
        channel: What channel you would like to join
        rejoin: Used by reconnect() to force rejoining of channels that
                are already in the channels dictionary.
    Returns:
        False: If given no channel, if it fails to send the join request, or
               if we have already joined the channel.
        True: When it succeeds at sending the join request

    """

    global channels
    if not channel:
        warnings.warn("join_channel() was not given a channel to join. Instead received an empty string.")
        return False
    elif channel in channels and not rejoin:
        warnings.warn("{} is already joined.".format(channel))
        return False
    else:
        if not _send_info("JOIN #%s\r\n" % channel):
            return False
        else:
            if channel not in channels.keys():
                channels[channel] = Channel(channel)
            return True


def leave_channel(channel: str, rejoin=False) -> bool:
    """
    Leaves a channel, stopping the API from receiving information related to
    that channel. Also removes the channel from the channels dictionary.

    Args:
        channel: Channel you would like to leave from
        rejoin: Used for stopping leave_channel from deleting the channel info

    Returns:
        False: If we never joined the channel, if no channel is given, or if we
               fail to send the leave request.
        True: When we succeed in sending the leave request.

    """
    global channels

    if not channel:
        warnings.warn("leave_channel() was not given a channel to leave. Instead received an empty string.")
        return False
    else:
        if channel not in channels.keys():
            warnings.warn("{} was not previously joined.".format(channel))
            return False
        else:
            irc_logger.info("Leaving {}".format(channel))
            if not _send_info("PART ${}".format(channel)):
                return False
            else:
                if not rejoin:
                    del channels[channel]
                return True


def rejoin_channel(channel: str) -> bool:
    """
    Rejoins a channel.

    Args:
        channel: The channel you would like to rejoin

    Returns:
        False: If given no channel, fails to leave, or fails to join the channel
        True: When it rejoins the channel
    """
    if not channel:
        warnings.warn("rejoin_channel was not given a channel to rejoin. Instead received an empty string.")
        return False
    else:
        irc_logger.info("Rejoining {}".format(channel))
        if not leave_channel(channel, True):
            return False
        else:
            if not join_channel(channel, True):
                return False
            else:
                return True


# Twitch Connection Management--------------------------------------------------
def connect(username: str, oauth: str, protocol="tcp", timeout_seconds=60) -> bool:
    """
    Connects to twitch, logging the user in.

    Args:
        username: Twitch username
        oauth: The oauth for that user
        protocol: Defaults to "tcp" can also be set to "udp'
        timeout_seconds: How long you'd like to wait for the connection to be
                         established before the function stops trying.
                         Defaults to 60 seconds.

    Returns:
        False: If already connected. If it times out. If there's an error when
               logging in (such as wrong username or pass).
        True: When it connects and logs in.
    Raises:
        ValueError: If given a protocol that is not "tcp" or "udp"
        ValueError: If no username or oauth is given

    """

    global is_connected
    global _CONNECTION_PROTOCOL
    global _SOCK
    global _username
    global _oauth

    # Do not attempt to connect if we're already connected.
    if is_connected:
        warnings.warn("Attempted to call connect while already connected. Use reconnect() if wanting to re-login.")
        return False

    # Make sure that we were given a protocol that we're able to use.
    if protocol is not "tcp" and protocol is not "udp":
        raise ValueError(
            "Protocol options are udp/tcp. Was given %s instead." % protocol
        )
    else:
        # Set the protocol that _send_info() will use.
        _CONNECTION_PROTOCOL = protocol

    # Make sure a username and oauth are given.
    if not username or not oauth:
        raise ValueError("No username/oauth given")

    # Connect to twitch
    irc_logger.info("Connecting to Twitch.")
    _SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _SOCK.settimeout(timeout_seconds)
    try:
        _SOCK.connect((_TWITCH, _PORT))
    except socket.error:
        irc_logger.error("Socket connection encountered an error while attempting to connect to Twitch.")
        _SOCK.close()
        return False

    # Save username and oauth for later use in reconnecting.
    _username = username
    _oauth = oauth

    # Log in
    irc_logger.info("Logging in...")
    _send_info("PASS %s\r\n" % oauth)
    _send_info("NICK %s\r\n" % username)

    # Check if the login details were correct
    # TODO: Move this over to get_info()? or a "check_login" function?
    response = _SOCK.recv(512).decode()
    if not response or "Login authentication failed" in response:
        warnings.warn("Login failed. Check username or oauth and try again.")
        _SOCK.close()
        return False
    else:
        irc_logger.info("Requesting IRCv3 membership, commands, and tags from Twitch.")
        # TODO: Check for NACK response from twitch if either of these fails
        # For an IRCv3 membership; Gives us NAMES, JOIN, PART, and MODE events
        _send_info("CAP REQ :twitch.tv/membership\r\n")
        # For enabling USERSTATE, GLOBALUSERSTATE, ROOMSTATE, HOSTTARGET, NOTICE
        # and CLEARCHAT raw commands.
        _send_info("CAP REQ :twitch.tv/commands\r\n")
        # For detailed information from messages (getting stuff like the user's
        # color, emotes, etc...
        _send_info("CAP REQ :twitch.tv/tags\r\n")

        is_connected = True
        return True


def disconnect():
    """
    Disconnects from twitch.

    Returns:
        False: If we're not connected to twitch in the first place
        True: If it disconnects

    """
    global _SOCK
    global is_connected

    if not _SOCK:
        warnings.warn("Disconnect() was called while not connected to twitch.")
        return False
    else:
        irc_logger.info("Disconnecting from Twitch.")
        _SOCK.close()
        is_connected = False
        return True


def reconnect():
    """
    Reconnects to twitch.

    Returns:
        False: If it fails to disconnect, and then connect to twitch, and then
                join all previously joined channels.
        True: When it succeeds in reconnecting.

    """
    global _RECONNECT

    if not disconnect():
        warnings.warn("Failed to disconnect from Twitch.")
        return False
    else:
        irc_logger.info("Reconnecting to Twitch.")
        if not connect(_username, _oauth):
            irc_logger.error("Failed to re-login to Twitch!")
            return False
        else:
            irc_logger.info("Attempting to rejoin previously joined channels.")
            for channel in channels.keys():
                if not join_channel(channel, True):
                    irc_logger.warning("Failed to rejoin {}!".format(channel))
                    return False
            _RECONNECT = False
            return True


def get_info(timeout_seconds=None) -> bool:
    """
    Gets information from twitch and hands it over to parsers. Also manages any
    PING's sent by twitch, automatically replying with a PONG.

    Args:
        timeout_seconds: How long you'd like to wait for a response before
                         disconnecting. Defaults to waiting forever.

    Returns:
        False: If it times out. If it can't decode the information. If it can't
               respond to a PING. If either of the Parsers fail.
        True: If all information is parsed or if a PONG is sent.

    """
    global _RECONNECT

    # Disable timeouts by default, in order to not disconnect from twitch no
    # matter how much time passes by.
    _SOCK.settimeout(timeout_seconds)
    try:
        information = _SOCK.recv(4096)
        # Check if socket is closed.
        if information == b'' or len(information) == 0:
            if _RECONNECT:
                irc_logger.info("Reconnecting to Twitch.")
                if not reconnect():
                    irc_logger.warning("Failed to reconnect to to Twitch.")
                    raise ConnectionAbortedError("Twitch has closed the connection.")
                return True
            irc_logger.warning("Twitch has closed the connection.")
            raise RuntimeError("Twitch has closed the connection.")
    except socket.timeout:
        disconnect()  # Unsure if I should disconnect or raise an error? Likely better to raise.
        return False

    # ??? We set user to None in here in order to make sure the user of this API
    # does not end up seeing a duplicate user object every time the loop
    # iterates and no chat line is sent from twitch(Since we don't update the
    # user object unless we get a new line in chat).
    global user
    global notification
    user = None
    notification = {}

    try:
        # ??? utf-8 is required, as twitch is a global platform and there are
        # times when a user might post in a character set that isn't ascii, such
        # as when typing in a foreign language. Without utf-8 decoding, the API
        # crashes at the sight of a foreign character.
        # TODO: Consider adding "errors='replace'" instead of the warning?
        information = information.decode('utf-8')
    except UnicodeDecodeError:
        # But sadly, the API still has some issues when it comes to unicode.
        # There are times when it is still unable to decode a character, causing
        # the API to crash. For this reason, for now, we simply return false
        # and ignore this single line of chat. Why "line of chat"? Because this
        # is the only time (as far as I know) that twitch sends us a character
        # that is not in the ASCII range, since users might choose to use
        # some rather strange characters.
        irc_logger.warning("Failed to decode Twitch data, discarding! There's a possibility that you may miss a chat "
                           "line if that was what caused the failure.")
        return False
    # TODO: For some reason this begins to be spammed at certain points.
    #       I believe the issue may have to do with Twitch closing the connection.
    #       Will know once I implement the Select module.
    # print(">>>GET_INFO_FULL: {}".format(information))

    if not information:
        return False
    elif "RECONNECT" in information and "PRIVMSG" not in information:  # Yet to be tested.
        # NOTE: Twitch does not show what the RECONNECT message/notification looks like. I'm left to a rough guess of
        #       what to search for. So for now, all I'm searching for is RECONNECT and making sure it's not a chat
        #       message.
        _RECONNECT = True
        pass
    elif information == "PING :tmi.twitch.tv\r\n":  # Ping Pong time.
        irc_logger.info("Received PING, sending PONG.")
        if not _send_info("PONG :tmi.twitch.tv\r\n"):
            return False
        else:
            return True
    else:
        irc_logger.info("Sending data over to parsers.")
        # Time to parse the information we received!
        for info in information.split('\n'):
            if info:
                # TODO: Maybe do checks for logging purposes?
                if info[0] == '@':
                    _manage_tags(info.strip())
                else:
                    _parse_irc(info.strip())
        return True
