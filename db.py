import os
import re
import sqlite3
import json

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

        rows = []
        for number in self.manifest:
            rows.append((number, self.manifest[number]["name"], self.manifest[number]["cost"], self.manifest[number]["rarity"]))

        cur.executemany("INSERT OR IGNORE INTO cards VALUES(?, ?, ?, ?, 0)", rows)
        self.conn.commit()

    def get_next_group(self, round_size):
        cur = self.conn.cursor()
        cost = self.get_lowest_cost()
        res = cur.execute("SELECT number, name, rarity FROM cards WHERE voted = 0 AND cost = ? LIMIT ?;", [(cost), (round_size)])
        return res.fetchall()
    
    def get_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM cards WHERE number=?", [(num)]).fetchone()[0]

    def get_img(self, num: int):
        return open(os.path.join(self.gallery_path, str(num)+".jpg"), mode="rb")
    
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