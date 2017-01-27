"""
Author: NekoGamiYuki
Version: 0.0.0

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
# TODO: Implement REGEX for both parsers.
# TODO: Check if twitch has implemented sub badge years into tags.
# TODO: Add local time to User class.

# TODO: Rewrite returns of all functions to take advantage of raising exceptions
# I want to make it so that I raise exceptions instead of just returning False.
# Things like not giving me a username when connecting are VERY serious, and
# therefore require an exception, a complete stop, rather than a return value.

# NOTE: Turns out you can actually PING twitch... The same way I send a PONG,
# but replace it with PING. They reply with a PONG. This is what I was doing
# accidentally this entire time...

# Imported Modules--------------------------------------------------------------
import socket
import time
import re

# Global Variables--------------------------------------------------------------
_SOCK = None
_TWITCH = "irc.chat.twitch.tv"  # Compliant with twitch's new server
_PORT = 6667  # Not using twitch's SSL capable server's

# Connection information
_CONNECTION_PROTOCOL = ''  # Do not set this yourself! Use connect() instead
is_connected = False

# Sending configuration
_commands_sent = 0
_send_time = 0
_RATE = 100  # No more than 100 commands sent every 30 seconds

# User information (for reconnecting)
_username = ''
_oauth = ''

# Twitch chat information
channels = {}
notification = ''  # Holds a single notification from twitch
user = None  # Once initialized by get_info() it contains a single users info

# Regular expressions-----------------------------------------------------------
# TODO: do a re.match for each of these to test which parser to send the information to?
# TODO: Maybe add r"$" to the end of each of these?
# Gets badges, a number and space (unknown why it does that...),
# extra information, COMMAND, channel, and message if available.
tags_regex = re.compile(r"^@((\w|\W)+;user-type=(\s|\w)+):(\w+!\w+@\w+\.tmi\.twitch\.tv) ([A-Z]+) #(\w+) :?([\S\s]+)?")
# Gets username, extra information, channel, and user's message.
irc_chat_regex = re.compile(r"^:(\w+)!(\w+@\w+\.tmi\.twitch\.tv) ([A-Z]+) #(\w+) :?([\S\s]+)?")
# Gets channel and string of all usernames.
names_start_regex = re.compile(r"^:\w+\.tmi\.twitch\.tv 353 \w+ = #(\w+) :([\S\s]+)?")
# Gets channel
names_end_regex = re.compile(r"^:\w+\.tmi\.twitch\.tv 356 \w+ #(\w+) :End of /NAMES list")
# Gets channel and username
join_part_regex = re.compile(r"^:(\w+)!(\w+@\w+\.tmi\.twitch\.tv) ([A-Z]+) #(\w+)")
#


# Classes-----------------------------------------------------------------------
class _Channel(object):
    """
    Contains information about a single channel. Such as their viewers, the
    message count (since you joined), whether they're in slow mode, etc...

    Information contained in class:
    name: Name of the channel
    moderators: Moderators of the channel, updated when a mod chats
    operators: General "mods", also includes admins and higher level users
    banned_users: All banned users since you joined, and any reasons for the ban
    timed_out_users: All users that have been timed out, and the seconds.
    viewers: A list of all viewers.
    language: If a channel designated a language, it goes here.
    slow: Whether the channel has slow mode on
    slow_time: The time for the slow mode cooldown
    r9k: Whether the channel has r9kbeta on
    subscriber: Whether the channel has subscriber-mode on
    hosting: Whether the channel is hosting
    hosted_channel: What channel is being hosted

    """

    def __init__(self, name=''):
        if name:
            self.name = name
        else:
            self.name = "UNASSIGNED"

        # How many messages were chatted since you joined
        self.message_count = 0
        self.moderators = []
        self.operators = []  # Use when we can't get exact info on moderators
        self.banned_users = {}
        self.timed_out_users = {}
        self.viewers = []
        self.language = ''
        self.slow = False
        self.slow_time = 0
        self.r9k = False
        self.subscriber = False
        self.hosting = False
        self.hosted_channel = ''


class _Emote(object):
    """
    Contains information relating to an emote. The Name, ID, and position in
    a string are provided.

    Inforamtion you can get from this class:
    name: Name of the emote
    id: Id of the emote, for use in other parts of the twitch API (not this one)
    position: Start and End position of the emote in the user's message

    """

    def __init__(self, name, id, start, end):
        self.name = name
        self.id = id
        self.position = {"start": start, "end": end}


class _User(object):
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
    emotes: A collection of _Emote objects, each relating to an emote the user
            used in chat.
    command: For bots, it's the first word in their message.

    Functions:
    ban(): Ban a user
    timeout(): Timeout a user
    send_message(): Sends a message to a user in chat
    """

    def __init__(self, info_congregation=None, filler_message="UNASSIGNED"):
        filler = filler_message  # For when we can't assign a value
        if not info_congregation:
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
                self.name = info_congregation["display-name"]
                if not self.name:
                    self.name = info_congregation["extra"].split("!")[0]
                self.message = info_congregation["message"]
                self.message_history = []
                # Where the user last chatted from
                self.chatted_from = info_congregation["chatted-from"]

                # Role information
                if self.name.lower() == self.chatted_from:
                    self.is_broadcaster = True
                else:
                    self.is_broadcaster = False
                # ??? Double conversion because bool would see '0' as true
                self.is_mod = bool(int(info_congregation["mod"]))
                self.is_sub = bool(int(info_congregation["subscriber"]))
                self.is_turbo = bool(int(info_congregation["turbo"]))

                # The user's role
                if info_congregation["user-type"] is ' ':
                    self.user_type = filler  # Admin, Staff, Mod, etc...
                else:
                    self.user_type = info_congregation["user-type"]

                # Styling information
                if not info_congregation["color"]:
                    self.color = filler
                else:
                    self.color = info_congregation["color"]

                self.badges = []
                if info_congregation["@badges"]:
                    for badge in info_congregation["@badges"].split(','):
                        self.badges.append(badge.split('/')[0])

                # Emotes!
                self.emotes = []
                if info_congregation["emotes"]:
                    for info in info_congregation["emotes"].split('/'):
                        for position in info.split(":")[1].split(','):
                            start = int(position.split('-')[0])
                            end = int(position.split('-')[1]) + 1
                            name = self.message[start:end]
                            self.emotes.append(_Emote(name,  # Name
                                                      info.split(":")[0],  # ID
                                                      start,  # Start position
                                                      end))  # end position

                # Bot information (Useful for bots) It's the first word of their
                # chat message.
                self.command = self.message.split()[0]
            except (KeyError, TypeError) as error_information:
                error_filler = ("ERROR: Please check  user._error if this "
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
                self._error = error_information

    def send_message(self, message, append_symbol=True):
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
        if append_symbol:
            formatted_message = "{}{} {}".format('@', self.name, message)
        else:
            formatted_message = "{} {}".format(self.name, message)

        if not chat(formatted_message, self.chatted_from):
            return False
        else:
            return True

    def timeout(self, seconds=600):
        """
        Times out this user.

        Args:
            seconds: The duration of the timeout in seconds. Default 600.

        Returns:
            True: When it succeeds in sending the timeout command to twitch
            False When it fails at sending the timeout command to twitch

        """
        if chat("/timeout {} {}".format(self.name, seconds), self.chatted_from):
            return True
        else:
            return False

    def ban(self, reason=''):
        """
        Permanently Bans this user. Can be given a reason, which shows up in
        chat as a twitch notification.

        Args:
            reason: The reason for banning the user

        Returns:
            True: If it succeeds at sending the Ban command to twitch.
            False: if it fails at sending the Ban command to twitch.

        """
        if reason:
            if chat("/ban {} {}".format(self.name, reason), self.chatted_from):
                return True
            else:
                return False
        else:
            if chat("/ban {}".format(self.name), self.chatted_from):
                return True
            else:
                return False


# Parsing-----------------------------------------------------------------------
# TODO: Create functions for managing each command. Use _manage_tags to determine
#       which function to use.
def _manage_tags(twitch_tags=''):
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
        twitch_tags: Tags are denoted by the '@' at the start of their line

    Returns:
        False: If it gets no tags or doesn't have a parser for the tags
        True: When it parses the tags

    """

    if not twitch_tags:
        return False
    else:

        print("Tags: {}".format(twitch_tags))
        print("Regex: {}".format(tag_regex.findall(twitch_tags)))  # DEBUG!!!

        # TODO: Consider whether I should do USERSTATE or GLOBALUSERSTATE since
        # PRIVMSG has the same tags.
        global user
        global channels
        global notification

        irc_command = ''
        number_of_hashes = twitch_tags.count('#')  # Or pounds, don't kill me
        # Get the IRC COMMAND that twitch sends, such as "PRIVMSG" or "NOTICE"
        if number_of_hashes is 1:
            irc_command = twitch_tags.split('#', 1)[0].split()[-1].strip()
        elif number_of_hashes > 1:
            # With tags, the user's color is sent as a hex value, starting with
            # a hash '#'. This causes a problem in the previous parsing
            # expression. We fix that rather easily by just parsing one more
            # hash.
            irc_command = twitch_tags.split('#', 2)[1].split()[-1].strip()

        # Time to parse the tags!
        if irc_command == "PRIVMSG":  # Chat lines
            main_info = twitch_tags.split('PRIVMSG', 1)

            # Separate information for splitting
            tags = main_info[0].rsplit(':', 1)[0].split(';')
            extra = main_info[0].rsplit(':', 1)[1]
            user_info = main_info[1].split(":", 1)

            info_congregation = {}

            for tag in tags:
                info_congregation[tag.split('=')[0]] = tag.split('=')[1]

            info_congregation["extra"] = extra.strip()
            info_congregation["chatted-from"] = \
                (user_info[0].strip().split('#')[1])
            if info_congregation["chatted-from"] in channels:
                channels[info_congregation["chatted-from"]].message_count += 1
            info_congregation["message"] = user_info[1].strip()

            user = _User(info_congregation)

            # Since we get to see if a user is a mod now, we add them to their
            # respective channel's moderator list
            # TODO: This breaks whenever I leave a channel. As the channel is deleted from the channels list.
            moderator_list = channels[user.chatted_from].moderators
            if user.is_mod and user.name not in moderator_list:
                channels[user.chatted_from].moderators.append(user.name)
            elif not user.is_mod and user.name in moderator_list:
                channels[user.chatted_from].moderators.remove(user.name)

            viewers = channels[user.chatted_from].viewers
            if user.name and user.name not in viewers:
                channels[user.chatted_from].viewers.append(user.name)

            return True
        elif irc_command == "NOTICE":  # Twitch NOTICE tag management
            main_info = twitch_tags.split(':')
            affected_channel = main_info[1].split('#')[1].strip()
            message_id = main_info[0].split('=')[1].strip()

            notification = "{} | {}".format(
                affected_channel, main_info[2].strip()
            )

            if "slow" in message_id:
                if "on" in message_id:
                    channels[affected_channel].slow = True
                else:
                    channels[affected_channel].slow = False
            elif "subs" in message_id:
                if "on" in message_id:
                    channels[affected_channel].subscriber = True
                else:
                    channels[affected_channel].subscriber = False
            elif "r9k" in message_id:
                if "on" in message_id:
                    channels[affected_channel].r9k = True
                else:
                    channels[affected_channel].r9k = False
            elif "host" in message_id:
                if "on" in message_id:
                    channels[affected_channel].hosting = True
                    channels[affected_channel].hosted_channel = (
                        notification.split()[-1].split('.')[0]
                    )
                else:
                    channels[affected_channel].hosting = False
                    channels[affected_channel].hosted_channel = ''
            return True
        elif irc_command == "ROOMSTATE":
            main_info = twitch_tags.split(":")
            channel_info = main_info[0].split('@')[1].split(';')
            affected_channel = main_info[1].split('#')[1].strip()

            for info in channel_info:
                tag_info = info.split('=')
                if "broadcaster-lang" in tag_info[0]:
                    channels[affected_channel].language = tag_info[1]
                elif "slow" in tag_info[0]:
                    if tag_info[1] == '0':
                        channels[affected_channel].slow = False
                        channels[affected_channel].slow_time = 0
                    else:
                        channels[affected_channel].slow = True
                        channels[affected_channel].slow_time = int(tag_info[1])
                elif "subs-only" in tag_info[0]:
                    if '0' in tag_info[1]:
                        channels[affected_channel].subscriber = False
                    else:
                        channels[affected_channel].subscriber = True
                elif "r9k" in tag_info[0]:
                    if '0' in tag_info[1]:
                        channels[affected_channel].r9k = False
                    else:
                        channels[affected_channel].r9k = True
            return True
        elif irc_command == "CLEARCHAT":
            main_info = twitch_tags.split(":")
            ban_info = {}
            if "reason" in main_info[0]:
                for info in main_info[0].split(';'):
                    ban_info[info.split('=')[0]] = info.split('=')[1]
            else:
                ban_info[main_info[0].split('=')[0]] = (
                    main_info[0].split('=')[1]
                )
            affected_channel = main_info[1].split('#')[1].strip()
            affected_user = main_info[2].strip()

            if len(ban_info) > 1:
                channels[affected_channel].timed_out_users[affected_user] = (
                    ban_info["@ban-duration"]
                )
            else:
                channels[affected_channel].banned_users[affected_user] = (
                    ban_info["@ban-reason"]
                )

            # TODO: Consider updating the notification var with timeout/ban info
            return True
        return False


# TODO: Manage names when joining a channel.
# TODO: Completely rewrite, use regex instead.
def _parse_irc(irc_info):
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
    if not irc_info:
        return False
    else:
        try:  # This try block is my cheap as hell way to save myself some work
            global channels
            global notification

            irc_command = irc_info.split('#', 1)[0].split()[-1].strip()
            affected_channel = irc_info.split('#', 1)[1].strip()

            # TODO: This seems to be bugged, so It doesn't always work
            # Managing NAMES given by twitch when you first join a channel
            if "353" in irc_info and '#' in irc_info:
                names = irc_info.split(':', 2)[2]
                names_affected_channel = (
                    irc_info.split(':', 2)[1].split('#')[1].strip()
                )
                name_list = []
                for name in names.split():
                    if name not in name_list:
                        name_list.append(name)
                for name in name_list:
                    if name not in channels[names_affected_channel].viewers:
                        channels[names_affected_channel].viewers.append(name)

            # Managing commands
            if irc_command == "JOIN":
                join_user = irc_info.split('!', 1)[0].split(':')[1].strip()
                if join_user not in channels[affected_channel].viewers:
                    channels[affected_channel].viewers.append(join_user)
                return True
            elif irc_command == "PART":
                join_user = irc_info.split('!', 1)[0].split(':')[1].strip()
                if join_user in channels[affected_channel].viewers:
                    channels[affected_channel].viewers.remove(join_user)
                return True
            elif irc_command == "MODE":
                mode = irc_info.split('#')[1].split()[1]
                affected_user = irc_info.split('#')[1].split()[-1]
                affected_channel = irc_info.split('#')[1].split()[0].strip()

                if mode == '+o':
                    if affected_user not in \
                            channels[affected_channel].operators:
                            channels[affected_channel].operators.append(
                            affected_user
                        )
                elif mode == '-o':
                    if affected_user in channels[affected_channel].moderators:
                        channels[affected_channel].operators.append(
                            affected_user
                        )
                return True
            elif irc_command == "HOSTTARGET":
                main_info = irc_info.split(':')
                affected_channel = main_info[0].split('#')[1].strip()
                target_channel = main_info[1].split()[0].strip()

                if (
                            not channels[affected_channel].hosting and
                            not channels[affected_channel].hosted_channel
                ):
                    channels[affected_channel].hosting = True
                    channels[affected_channel].hosted_channel = target_channel
                elif (
                                channels[affected_channel].hosting and
                                channels[affected_channel].hosted_channel and
                                target_channel == '-'
                ):
                    channels[affected_channel].hosting = False
                    channels[affected_channel].hosted_channel = ''
                return True
            elif irc_command == "PRIVMSG":
                # TODO: Debug notifications
                main_info = irc_info.split(':', 2)
                sender = main_info[1].split('!')[0].strip()
                affected_channel = main_info[1].split("#", 1)[1].strip()
                sub_resub_notification = main_info[2].strip()
                if sender == "twitchnotify":
                    notification = "{} | {}".format(
                        affected_channel, sub_resub_notification
                    )
            elif irc_command == "RECONNECT":
                if not reconnect():
                    return False
                else:
                    return True
        except IndexError:
            return False


# Twitch Communication----------------------------------------------------------
# TODO: Actually increment the "commands_sent" variable.
def _send_info(info):
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
            # ??? There's a chance that we might disconnect or have a hiccup
            try:
                # NOTE: Do not loop in an attempt to resend possibly incomplete
                # info as you will face the consequences... 2 hours of waiting
                # here I come...
                if _CONNECTION_PROTOCOL is "tcp":
                    _SOCK.send(info.encode("utf-8"))
                    return True
                elif _CONNECTION_PROTOCOL is "udp":
                    _SOCK.sendto(info.encode("utf-8"), (_TWITCH, _PORT))
                    return True
            except InterruptedError:
                return False


# Twitch Interaction------------------------------------------------------------
def chat(message='', channel=''):
    """
    Sends a chat message toa specific channel.

    Args:
        message: What you would like to send to the channel's chat
        channel: The channel you'd like to send the message to

    Returns:
        True: When it sends the message
        False: if it is given an empty string or is unable to send the message
    """
    if not message or not channel:
        return False
    else:
        if not _send_info("PRIVMSG #{} :{}\r\n".format(channel, message)):
            return False
        else:
            return True


def join_channel(channel='', rejoin=False):
    """
    Joins a channel's chat, allowing the API to recieve information from that
    channel. Updates the channels variable with a new channel object, named
    after the channel you've joined.

    Args:
        channel: What channel you would like to join
        rejoin: Used by reconnect() to force rejoining of channels that
                are already in the channels list.
    Returns:
        False: If given no channel or if it fails to send the join request, or
               if we have already joined the channel.
        True: When it succeeds at sending the join request

    """

    global channels

    if not channel or channel in channels and not rejoin:
        return False
    else:
        if not _send_info("JOIN #%s\r\n" % channel):
            return False
        else:
            if channel not in channels.keys():
                channels[channel] = _Channel(channel)
            return True


def leave_channel(channel, rejoin=False):
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
        return False
    else:
        if channel not in channels.keys():
            return False
        else:
            if not _send_info("PART ${}".format(channel)):
                return False
            else:
                if not rejoin:
                    del channels[channel]
                return True


def rejoin_channel(channel=''):
    """
    Rejoins a channel.

    Args:
        channel: The channel you would like to rejoin

    Returns:
        False: If given no channel, fails to leave, or fails to join the channel
        True: When it rejoins the channel
    """
    if not channel:
        return False
    else:
        if not leave_channel(channel, True):
            return False
        else:
            if not join_channel(channel, True):
                return False
            else:
                return True


# Twitch Connection Management--------------------------------------------------
def connect(username='', oauth='', protocol="tcp", timeout_seconds=60):
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

    # Do not attempt to connect if we're already connected!
    if is_connected:
        return False

    # Make sure that we were given a protocol that we're able to use
    if protocol is not "tcp" and protocol is not "udp":
        raise ValueError(
            "Protocol options are udp/tcp. Was given %s instead." % protocol
        )
    else:
        # Set the protocol that _send_info() will use
        _CONNECTION_PROTOCOL = protocol

    # Make sure a username and oauth are given
    if not username or not oauth:
        raise ValueError("No username/oauth given")

    # Connect to twitch
    _SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _SOCK.settimeout(timeout_seconds)
    try:
        _SOCK.connect((_TWITCH, _PORT))
    except socket.error:
        _SOCK.close()
        return False

    # Save username and oauth for later use in reconnecting.
    _username = username
    _oauth = oauth

    # Log in
    _send_info("PASS %s\r\n" % oauth)
    _send_info("NICK %s\r\n" % username)

    # Check if the login details were correct
    response = _SOCK.recv(512).decode()
    if not response or "Error logging in" in response:
        _SOCK.close()
        return False
    else:
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
        return False
    else:
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
    if not disconnect():
        return False
    else:
        if not connect(_username, _oauth):
            return False
        else:
            for channel in channels.keys():
                if not join_channel(channel, True):
                    return False
            return True


def get_info(timeout_seconds=None):
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
    # Disable timeouts by default, in order to not disconnect from twitch no
    # matter how much time passes by.
    _SOCK.settimeout(timeout_seconds)
    try:
        information = _SOCK.recv(4096)
    except socket.timeout:
        disconnect()
        return False

    # ??? We set user to None in here in order to make sure the user of this API
    # does not end up seeing a duplicate user object every time the loop
    # iterates and no chat line is sent from twitch(Since we don't update the
    # user object unless we get a new line in chat).
    global user
    global notification
    user = None
    notification = ''

    #TODO: Consider throwing an error instead of ignoring the chat message.
    try:
        # ??? utf-8 is required, as twitch is a global platform and there are
        # times when a user might post in a character set that isn't ascii, such
        # as when typing in a foreign language. Without utf-8 decoding, the API
        # crashes at the sight of a foreign character.
        information = information.decode('utf-8')
    except UnicodeDecodeError:
        # But sadly, the API still has some issues when it comes to unicode.
        # There are times when it is still unable to decode a character, causing
        # the API to crash. For this reason, for now, we simply return false
        # and ignore this single line of chat. Why "line of chat"? Because this
        # is the only time (as far as I know) that twitch sends us a character
        # that is not in the ASCII range, since users might choose to use
        # some rather strange characters.
        return False

    if not information:
        return False
    elif information == "RECONNECT":
        # TODO: Add reconnect functionality
        pass
    elif information == "PING :tmi.twitch.tv\r\n":  # Ping Pong time.
        if not _send_info("PONG :tmi.twitch.tv\r\n"):
            return False
        else:
            return True
    else:
        # Time to parse the information we received!
        for info in information.split('\n'):
            try:
                if info[0] == '@':
                    if not _manage_tags(info):
                        return False
                    else:
                        return True
                else:
                    if not _parse_irc(info):
                        return False
                    else:
                        return True
            except IndexError:
                pass
