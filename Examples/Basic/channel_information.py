"""
This example file will show how to some basic information of the channel's you
have joined. We will see how many viewers are in chat, whether the channel is
in slow/subscriber mode, and if it is hosting a channel, as well as what channel
is being hosted.

Replace the necessary parameters (such as "username") with your own.
"""

import sys
from spicytwitch import irc

if not irc.connect("username", "oauth:..."):
    print("Unable to log in!")
    sys.exit(1)

some_twitch_channel = "my_channel"
irc.join_channel(some_twitch_channel)

while True:
    if irc.get_info():
        print("-"*80)  # A simple spacer to separate output for readability

        # viewers is a list of all viewers in chat, as reported by twitch, also
        # updated if a user that chats isn't in the list.
        if irc.channels[some_twitch_channel].viewers:
            print("There are currently {} viewers in this channel".format(
                len(irc.channels[some_twitch_channel].viewers)
            ))

        # Checking if the channel has slow mode on, and how many seconds it is
        # set to.
        if irc.channels[some_twitch_channel].slow:

            print("The channel is in slow mode! {} seconds".format(
                irc.channels[some_twitch_channel].slow_time
            ))
        else:
            print("The channel is not in slow mode.")

        # Checking for subscriber-only mode
        if irc.channels[some_twitch_channel].subscriber:
            print("The channel is in subscriber-only mode!")
        else:
            print("The channel is not in subscriber-only mode.")

        # Seeing who the channel is hosting.
        if irc.channels[some_twitch_channel].hosting:
            print("The channel is hosting {}!".format(
                irc.channels[some_twitch_channel].hosted_channel
            ))
