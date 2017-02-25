"""
This example file shows how to send a message to a twitch channel. It waits
30 seconds before sending the same message again, so as to not spam the channel.

WARNING: Please do not remove the time.sleep(), or lower it, as you may get
banned from twitch for a certain amount of time. Do so only if  you know what
you are doing.

Replace the necessary parameters (such as "username") with your own.
"""

import sys
import time
from SpicyTwitch import irc

# Connect to twitch, make sure we've logged in.
if not irc.connect("username", "oauth:..."):
    print("Unable to login!")
    sys.exit(1)  # Close the program if we can't login

# Go ahead and set it to your own channel.
my_channel = "my_channel"
irc.join_channel(my_channel)

while True:
    if irc.get_info():
        # Wait 30 seconds before sending another message as we don't want to
        # spam the channel...
        time.sleep(30)
        # chat() requires two parameters; First is the message you'd like to
        # send. Second is the channel you would like to send that message to.
        irc.chat("Hey! I'm chatting! Kappa Kappa MingLee", my_channel)
