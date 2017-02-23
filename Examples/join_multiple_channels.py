"""
This example file shows how to join multiple channels by iterating over a list
of channel names.

Replace the necessary parameters (such as "username") with your own.
"""

import sys
import twitch

# Connect to twitch, make sure we've logged in.
if not twitch.connect("username", "oauth:..."):
    print("Unable to login!")
    sys.exit(1)  # Close the program if we can't login

# Joining multiple channels is incredibly simple. All you need to do is iterate
# over a list/dict of strings that contain channel names, and run join_channel()
# for each of those. I would suggest creating the list from user input, so that
# you may join different channels depending on your needs, if possible.
channels = ["some_channel_1", "some_channel_2", "some_channel_3"]
for channel in channels:
    twitch.join_channel(channel)
# You can see what channel's you've joined by looking at twitch.channels.keys()

while True:
    if twitch.get_info():
        # Do some stuff!
        pass  # Remember to remove this if you use the example file!
