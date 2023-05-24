import os

from bot import bot, setup
from db import DB

# The file to store the backing data in
SQLITE_FILE = "data.db"

# The path to the JSON card metadata manifest
MANIFEST_PATH = "manifest.json"

# The path to the JSON map metadata manifest
MAPIFEST_PATH = "mapifest.json"

# The path to a folder containing all the cards' images
GALLERY_PATH = "gallery"

# When True, delete our own messages after tallying the votes on them
SHOULD_DELETE_MESSAGES = True

def main():
    db = DB(SQLITE_FILE, MANIFEST_PATH, MAPIFEST_PATH, GALLERY_PATH)
    setup(bot, db, should_delete_messages = SHOULD_DELETE_MESSAGES)
    bot.run(os.getenv("TABLE_TURF_TOKEN"))

if __name__ == "__main__":
    main()