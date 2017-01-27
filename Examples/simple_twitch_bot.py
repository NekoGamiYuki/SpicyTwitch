"""
This example file will show how to setup a simple twitch bot that has 3
commands. One command per level of user, starting with the viewer, then mod,
and finally broadcaster. It will reply something based on whether that user
has permission to use the command. The bot will also time out anyone that says
"your bot is a scrub"  for the fun of it.

WARNING: Please deploy this example in your own channel. Only place it in
another channel if you have explicit permission (Why though...?).

Replace the necessary parameters (such as "username") with your own.
"""

import sys
import twitch

if not twitch.connect("username", "oauth:..."):
    print("Unable to login!")
    sys.exit(1)

twitch.join_channel("my_channel")

while True:
    if twitch.get_info():
        if twitch.user:
            # COMMANDS! --------------------------------------------------------
            # No need to check if the user is a mod or broadcaster, simply
            # let them use the command since it's for everyone!
            command = twitch.user.comamnd.lower()
            if command == "!viewer":
                # By default, send_message attaches the users name, with a
                # leading '@' symbol. If you do not want the '@' symbol you
                # can set the second, optional, parameter to False, like this:
                # twitch.user.send_message("massage", False)
                # If you do not want their name to be shown at all, use chat()
                # instead of the user's send_message()
                twitch.user.send_message("You're a viewer!")
            elif twitch.user.is_mod and command == "!moderator":
                # This time we made sure to check that the user was a moderator
                # in order to limit the command to moderators.
                twitch.user.send_message("My god, you're a moderator!")
            elif twitch.user.is_broadcaster and command == "!broadcaster":
                # As with before, we are checking if the user is a broadcaster
                # in order to limit the command to the channel owner.
                twitch.user.send_message("Whoa, you're the channel owner!")

            # Automated Timeout ------------------------------------------------
            bannable_phrase = "your bot is a scrub"
            # Make sure to make the message lowercase, that way we don't run
            # into problems with them capitalizing different parts of the phrase
            if bannable_phrase in twitch.user.message.lower():
                # By default, timeout() is set to 600 seconds, but we want to
                # simply test this, so we'll set it to 5 seconds.
                twitch.user.timeout(5)
