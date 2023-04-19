# Tableturf Bot

This is a discord bot used for conducting tier-list polls for Splatoon's [Tableturf Battle](https://splatoonwiki.org/wiki/Tableturf_Battle) cards.

It requires a directory of card images, named with their numbers, names, and rarities in order to run. These files are bundled into the repo for convenience.

It exposes a few commands, to start/stop rounds of voting. Voting is performed by reacting to the bot's messages in a discord channel.

When votes are tallied, the bot removes the top and bottom 10% of votes, then computes a weighted average of the remaining votes. These weighted averages will later be sorted and grouped into tier lists.

# Dependencies

- `sqlite3`
- `pycord`
- `asyncio`

# Running

The bot expects a discord bot token in the `TABLE_TURF_TOKEN` environment variable. After setting it, just run `main.py`.

There are some configuration options exposed as global constants in `main.py`.

All voting data will be stored in a sqlite3 database, with which you can do whatever you like.

# License

MIT