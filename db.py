import os
import re
import sqlite3
import json

class DB:
    def __init__(
            self,
            fname: str,
            manifest_path: str,
            # hehe.
            mapifest_path: str,
            sleeve_manifest_path: str,
            gallery_path: str
    ):
        self.conn = sqlite3.connect(fname)
        self.gallery_path = gallery_path
        cur = self.conn.cursor()

        with open(mapifest_path) as f:
            self.mapifest = json.loads(f.read())

        with open(manifest_path) as f:
            self.manifest = json.loads(f.read())

        with open(sleeve_manifest_path) as f:
            self.sleeve_manifest = json.loads(f.read())

        # "Why not have one table - say, 'entities' - with a 'type' column"?
        #
        # Don't think about it, hacky is the spirit of the exercise.
        cur.execute("""CREATE TABLE IF NOT EXISTS cards(
            number INTEGER PRIMARY KEY,
            name VARCHAR(255),
            cost INTEGER,
            rarity VARCHAR(255),
            voted INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS maps(
            number INTEGER PRIMARY KEY,
            name VARCHAR(255),
            voted INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS sleeves(
            number INTEGER PRIMARY KEY,
            name VARCHAR(255),
            voted INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS sleeve_votes(
            number INTEGER,
            score INTEGER,
            votes INTEGER,
            PRIMARY KEY (number, score)
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS map_votes(
            number INTEGER,
            score INTEGER,
            votes INTEGER,
            PRIMARY KEY (number, score)
        )""")
    
        cur.execute("""CREATE TABLE IF NOT EXISTS votes(
            number INTEGER,
            score INTEGER,
            votes INTEGER,
            PRIMARY KEY (number, score)
        )""")

        # hack: "map", "card", "sleeve"; default card
        cur.execute("""CREATE TABLE IF NOT EXISTS round_type(
            thing VARCHAR(255)
        )""")

        # List of in-flight messages
        cur.execute("""CREATE TABLE IF NOT EXISTS messages(
            channel_id INTEGER,
            id INTEGER,
            number INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS summaries(
            channel_id INTEGER,
            id INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS forum_posts(
            id INTEGER
        )""")

        cur.execute("""CREATE TABLE IF NOT EXISTS forum_chan(
            channel_id INTEGER
        )""")

        rows = []
        for number in self.manifest:
            rows.append((number, self.manifest[number]["name"], self.manifest[number]["cost"], self.manifest[number]["rarity"]))

        cur.executemany("INSERT OR IGNORE INTO cards VALUES(?, ?, ?, ?, 0)", rows)
        
        rows = []
        for number in self.mapifest:
            rows.append((number, self.mapifest[number]["name"]))

        cur.executemany("INSERT OR IGNORE INTO maps VALUES(?, ?, 0)", rows)

        rows = []
        for number in self.sleeve_manifest:
            rows.append((number, self.sleeve_manifest[number]["name"]))

        cur.executemany("INSERT OR IGNORE INTO sleeves VALUES(?, ?, 0)", rows)

        self.conn.commit()

    def get_round_type(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT thing FROM round_type").fetchone()
        return "card" if not res else res[0]

    def set_round_type(self, typ :str):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM round_type")
        cur.execute("INSERT INTO round_type VALUES(?)", [(typ)])
        self.conn.commit()

    def set_forum_chan(self, id):
        cur = self.conn.cursor()
        # Drop whatever is in it
        cur.execute("DELETE FROM forum_chan")
        cur.execute("INSERT INTO forum_chan VALUES(?)", [(id)])
        self.conn.commit()

    def get_forum_chan(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT channel_id FROM forum_chan").fetchone()
        return res if not res else res[0]

    def get_card_group(self, round_size):
        cur = self.conn.cursor()
        cost = self.get_lowest_cost()
        res = cur.execute("SELECT number, name, rarity FROM cards WHERE voted = 0 AND cost = ? ORDER BY RANDOM() LIMIT ?;", [(cost), (round_size)])
        return res.fetchall()

    def get_map_group(self, round_size):
        cur = self.conn.cursor()
        res = cur.execute("SELECT number, name FROM maps WHERE voted = 0 ORDER BY RANDOM() LIMIT ?;", [(round_size)])
        return res.fetchall()

    def get_sleeve_group(self, round_size):
        cur = self.conn.cursor()
        res = cur.execute("SELECT number, name FROM sleeves WHERE voted = 0 ORDER BY RANDOM() LIMIT ?;", [(round_size)])
        return res.fetchall()

    def get_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM cards WHERE number=?", [(num)]).fetchone()[0]

    def get_map_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM maps WHERE number=?", [(num)]).fetchone()[0]

    def get_sleeve_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM sleeves WHERE number=?", [(num)]).fetchone()[0]

    def get_img(self, num: int, typ: str):
        path = str(num)+".jpg"
        if typ != "card":
            path = typ + "_" + str(num) + ".png"
        return open(os.path.join(self.gallery_path, path), mode="rb")
    
    def insert_summaries(self, msgs):
        cur = self.conn.cursor()
        cur.executemany("INSERT OR IGNORE INTO summaries VALUES(?, ?)", msgs)
        self.conn.commit()

    def get_summaries(self, channel_id):
        cur = self.conn.cursor()
        res = cur.execute("SELECT id FROM summaries WHERE channel_id = ?", [(channel_id)]).fetchall()
        return res

    def remove_summary(self, msg_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM summaries WHERE id = ?", [(msg_id)])
        self.conn.commit()

    def insert_messages(self, msgs):
        cur = self.conn.cursor()
        cur.executemany("INSERT OR IGNORE INTO messages VALUES(?, ?, ?)", msgs)
        self.conn.commit()

    def insert_forum_posts(self, msgs):
        cur = self.conn.cursor()
        cur.executemany("INSERT OR IGNORE INTO forum_posts VALUES(?)", msgs)
        self.conn.commit()

    def get_forum_posts(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT id FROM forum_posts").fetchall()
        return res

    def remove_forum_post(self, id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM forum_posts WHERE id = ?", [(id)])
        self.conn.commit()

    def get_messages(self, channel_id):
        cur = self.conn.cursor()
        res = cur.execute("SELECT id, number FROM messages WHERE channel_id = ?", [(channel_id)]).fetchall()
        return res
    
    def add_scores(self, number, scores):
        cur = self.conn.cursor()
        rows = [(number, x+1, scores[x]) for x in range(len(scores))]
        res = cur.executemany("INSERT OR REPLACE INTO votes VALUES(?, ?, ?)", rows)
        self.conn.commit()

    def add_map_scores(self, number, scores):
        cur = self.conn.cursor()
        rows = [(number, x+1, scores[x]) for x in range(len(scores))]
        res = cur.executemany("INSERT OR REPLACE INTO map_votes VALUES(?, ?, ?)", rows)
        self.conn.commit()

    def add_sleeve_scores(self, number, scores):
        cur = self.conn.cursor()
        rows = [(number, x+1, scores[x]) for x in range(len(scores))]
        res = cur.executemany("INSERT OR REPLACE INTO sleeve_votes VALUES(?, ?, ?)", rows)
        self.conn.commit()

    def mark_has_voted(self, number):
        cur = self.conn.cursor()
        cur.execute("UPDATE cards SET voted = 1 WHERE number=?", [(number)])
        self.conn.commit()

    def mark_map_has_voted(self, number):
        cur = self.conn.cursor()
        cur.execute("UPDATE maps SET voted = 1 WHERE number=?", [(number)])
        self.conn.commit()

    def mark_sleeve_has_voted(self, number):
        cur = self.conn.cursor()
        cur.execute("UPDATE sleeves SET voted = 1 WHERE number=?", [(number)])
        self.conn.commit()

    def number_for_name(self, name):
        cur = self.conn.cursor()
        res = cur.execute("SELECT number FROM cards WHERE name=?", [(name)]).fetchone()[0]
        return res

    def remove_message(self, msg_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM messages WHERE id = ?", [(msg_id)])
        self.conn.commit()

    def get_lowest_cost(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT MIN(cost) FROM cards WHERE voted = 0").fetchone()
        return 99 if not res else res[0]
    
    def number_for_cost(self, cost):
        cur = self.conn.cursor()
        res = cur.execute("SELECT COUNT(*) FROM cards WHERE cost = ? AND voted = 0", [(cost)]).fetchone()
        return res[0]

    def maps_left(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT COUNT(*) FROM maps WHERE voted = 0").fetchone()
        return res[0]

    def sleeves_left(self):
        cur = self.conn.cursor()
        res = cur.execute("SELECT COUNT(*) FROM sleeves WHERE voted = 0").fetchone()
        return res[0]