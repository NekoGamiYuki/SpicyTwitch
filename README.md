#SpicyTwitchIRC (Soon to be known as just SpicyTwitch)
A simple Python module for communicating with twitch chat via IRC.

## Is it stable?
Not just yet.

## Can I use this?
Go ahead, just know that it's still in development and will have many changes as
I continue to develop it. I'm also rather new to developing software at this
scale (I'm developing this for use in a Twitch Bot) so you might find some code
that you feel could be done better.

## Why is it using 'sfh' emotes?
Because it was developed primarily for the purpose of being a bot in sly's
channel. I'm working on a set of basic emotes that the command modules can use
and a bot can quickly alter. That way changing emotes won't have to be tedious.

## The commands in the Bot section are... unique.
That's because they are being developed for use in Slyfoxhound's channel. So
it's likely that some of those commands may not be what you'd like to have on
your bot. I intend on working on ways to disable commands, however if you want
to use the code right now then you can just delete the command modules that you
don't need (other than module_tools, general, command_manager, and bot_tools)

For the meantime these will stay where they are, however if necessary I'll move
them into a separate section, maybe a "SpicyTwitch.bot.extra" that isn't auto
imported.


## Any big plans?
I intend to turn this into a full-blown package for building twitch bots. I'm
unsure if this is something I'll be continuing to support for years to come, but
for the time being it is my main project.
