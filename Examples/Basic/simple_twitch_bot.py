"""
This example file will show how to setup a simple twitch bot that has 3
commands. One command per level of user, starting with the viewer, then mod,
and finally broadcaster. It will reply something based on what command and
permissions the user has. The bot will also time out anyone that says
"your bot is a scrub"  for the fun of it.

WARNING: Please deploy this example in your own channel. Only place it in
another channel if you have explicit permission (Why though...?).

Replace the necessary parameters (such as "username") with your own.
"""

import sys
from spicytwitch import irc

if not irc.connect("username", "oauth:..."):
    print("Unable to login!")
    sys.exit(1)

irc.join_channel("my_channel")

while True:
    if irc.get_info():
        if irc.user:
            # COMMANDS! --------------------------------------------------------
            # user.command is set to the first "word" (split by a space) of the
            # user's message.
            command = irc.user.comamnd.lower()
            # No need to check if the user is a mod or broadcaster for the first
            # command, simply let them use the command since it's for everyone!
            if command == "!viewer":
                # By default, send_message attaches the users name, with a
                # leading '@' symbol. If you do not want the '@' symbol you
                # can set the second, optional, parameter to False, like this:
                # twitch.user.send_message("massage", False)
                # If you do not want their name to be shown at all, use chat()
                # instead of the user's send_message()
                irc.user.send_message("You're a viewer!")
            elif irc.user.is_mod and command == "!moderator":
                # This time we made sure to check that the user was a moderator
                # in order to limit the command to moderators. Note, that this
                # will not allow a streamer to use the command, as twitch does
                # not report them as moderators when they send messages. Instead
                # if you'd like the broadcaster to use mod commands you should
                # make sure to check user.is_broadcaster as well.
                irc.user.send_message("My god, you're a moderator!")
            elif irc.user.is_broadcaster and command == "!broadcaster":
                # And now we are checking if the user is a broadcaster in order
                # to limit the command to the channel owner.
                irc.user.send_message("Whoa, you're the channel owner!")

            # Automated Timeout ------------------------------------------------
            bannable_phrase = "your bot is a scrub"
            # Make sure to make the message lowercase, that way we don't run
            # into problems with them capitalizing different parts of the phrase
            if bannable_phrase in irc.user.message.lower():
                # By default, timeout() is set to 600 seconds, but we want to
                # simply test this, so we'll set it to 5 seconds.
                irc.user.timeout(5)

                # You can also give a reason for the timeout, like this:
                # twitch.user.timeout(5, "I am not a scrub!")
