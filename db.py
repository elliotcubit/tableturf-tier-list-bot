import os
import re
import sqlite3
import json

# Things already voted on before the bot existed
has_voted = """Splatana Wiper
Octostamp
Tri-Slosher
Tri-Slosher Nouveau
Curling Bomb
Custom Splattershot Jr.
Splattershot Jr.
Octomissile
Torpedo
Octocopter
Suction Bomb
Smallfry
Splat Bomb
Fizzy Bomb
Tentatek
Sprinkler
Octopod
Burst Bomb
Point Sensor
N-ZAP '85
Ink Mine
Toxic Mist
Trizooka
Big Bubbler
Zipcaster
Tenta Missiles
Ink Storm
Booyah Bomb
Wave Breaker
Ink Vac
Killer Wail 5.1
Inkjet
Ultra Stamp
Crab Tank
Reefslider
Triple Inkstrike
Zink Mini Splatling
Tacticooler
Kraken Royale
Super Chump""".split("\n")

class DB:
    def __init__(self, fname: str, manifest_path: str, gallery_path: str):
        self.conn = sqlite3.connect(fname)
        self.gallery_path = gallery_path
        cur = self.conn.cursor()

        with open(manifest_path) as f:
            self.manifest = json.loads(f.read())

        cur.execute("""CREATE TABLE IF NOT EXISTS cards(
            number INTEGER PRIMARY KEY,
            name VARCHAR(255),
            cost INTEGER,
            rarity VARCHAR(255),
            voted INTEGER
        )""")
    
        cur.execute("""CREATE TABLE IF NOT EXISTS votes(
            number INTEGER,
            score INTEGER,
            votes INTEGER,
            PRIMARY KEY (number, score)
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

        rows = []
        for number in self.manifest:
            rows.append((number, self.manifest[number]["name"], self.manifest[number]["cost"], self.manifest[number]["rarity"]))

        cur.executemany("INSERT OR IGNORE INTO cards VALUES(?, ?, ?, ?, 0)", rows)
        
        for thing in has_voted:
            num = self.number_for_name(thing)
            self.mark_has_voted(num)
        
        self.conn.commit()

    def get_next_group(self, round_size):
        cur = self.conn.cursor()
        cost = self.get_lowest_cost()
        res = cur.execute("SELECT number, name, rarity FROM cards WHERE voted = 0 AND cost = ? ORDER BY RANDOM() LIMIT ?;", [(cost), (round_size)])
        return res.fetchall()
    
    def get_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM cards WHERE number=?", [(num)]).fetchone()[0]

    def get_img(self, num: int):
        return open(os.path.join(self.gallery_path, str(num)+".jpg"), mode="rb")
    
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

    def get_messages(self, channel_id):
        cur = self.conn.cursor()
        res = cur.execute("SELECT id, number FROM messages WHERE channel_id = ?", [(channel_id)]).fetchall()
        return res
    
    def add_scores(self, number, scores):
        cur = self.conn.cursor()
        rows = [(number, x+1, scores[x]) for x in range(len(scores))]
        res = cur.executemany("INSERT OR REPLACE INTO votes VALUES(?, ?, ?)", rows)
        self.conn.commit()

    def mark_has_voted(self, number):
        cur = self.conn.cursor()
        cur.execute("UPDATE cards SET voted = 1 WHERE number=?", [(number)])
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
        return res[0]
    
    def number_for_cost(self, cost):
        cur = self.conn.cursor()
        res = cur.execute("SELECT COUNT(*) FROM cards WHERE cost = ? AND voted = 0", [(cost)]).fetchone()
        return res[0]