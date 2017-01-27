"""
This example shows how to connect to twitch and print out the
username and messages from chat.

TIP: If you're joining multiple channels, you can organize output by
having the channel they chatted from alongside their message (or if you're
making a graphical application, sending it to the corresponding window)
Replace the necessary parameters (such as "username") with your own. You can
get the channel a user chatted from by checking twitch.user.chatted_from
"""

import sys
import twitch

# Connect to twitch, make sure we've logged in.
if not twitch.connect("username", "oauth:..."):
    print("Unable to log in!")
    sys.exit(1)  # Close the program if we can't login

# Join a channel
twitch.join_channel("my_channel")

# The main loop of our program, which will request information from twitch,
# including getting the latest lines of chat from the channels that have been
# joined.
while True:
    # Get info from twitch to be up to date with the chat.
    # If we did, run our code.
    if twitch.get_info():
        # A single user's information is stored in the user variable. This is
        # updated every time we get a new line in chat. The API is setup to work
        # with a single user at a time, based on the latest information we've
        # relieved from twitch, keep this in mind. Whenever the API doesn't get
        # a new chat line, it sets the user variable to "None", so we have to
        # make sure to check for that.
        if twitch.user:
            # The user.name is their Username. The chat message they wrote is
            # stored in user.message.
            print("{}: {}".format(twitch.user.name, twitch.user.message))

