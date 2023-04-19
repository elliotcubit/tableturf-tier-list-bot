import os

from bot import bot, setup
from db import DB

# The file to store the backing data in
SQLITE_FILE = "data.db"

# The path to a folder containing all the cards' images
GALLERY_PATH = "gallery"

# Number of cards to vote on at the same time
ROUND_SIZE = 1

# When True, delete our own messages after tallying the votes on them
SHOULD_DELETE_MESSAGES = False

def main():
    db = DB(SQLITE_FILE, GALLERY_PATH, round_size=ROUND_SIZE)
    setup(bot, db, should_delete_messages = SHOULD_DELETE_MESSAGES)
    bot.run(os.getenv("TABLE_TURF_TOKEN"))

if __name__ == "__main__":
    main()