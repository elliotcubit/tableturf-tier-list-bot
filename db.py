import os
import re
import sqlite3

class DB:
    def __init__(self, fname: str, gallery_path: str, round_size: int = 4):
        self.conn = sqlite3.connect(fname)
        self.gallery_path = gallery_path
        self.round_size = round_size
        cur = self.conn.cursor()

        cur.execute("""CREATE TABLE IF NOT EXISTS cards(
            number INTEGER PRIMARY KEY,
            name VARCHAR(255),
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

        prog = re.compile("No. (\d+) (.*) \((.*)\).jpg")

        data = []
        for _root, _dirs, files in os.walk(gallery_path):
            for fname in files:
                result = prog.match(fname)
                if not result:
                    continue

                number = int(result.group(1))
                name = result.group(2)
                rarity = result.group(3)
                data.append((number, name, rarity))

        cur.executemany("INSERT OR IGNORE INTO cards VALUES(?, ?, ?, 0)", data)
        self.conn.commit()

    def get_next_group(self):
        cur = self.conn.cursor()
        res = cur.execute(f"SELECT number, name, rarity FROM cards WHERE voted = 0 ORDER BY RANDOM() LIMIT {self.round_size};")
        return res.fetchall()
    
    def get_name(self, num: int):
        cur = self.conn.cursor()
        return cur.execute("SELECT name FROM cards WHERE number=?", [(num)]).fetchone()[0]

    def get_img(self, num: int):
        cur = self.conn.cursor()
        res = cur.execute("SELECT number, name, rarity FROM cards WHERE number=?", [(num)]).fetchone()
        imgname = f"No. {res[0]} {res[1]} ({res[2]}).jpg"
        return open(os.path.join(self.gallery_path, imgname), mode="rb")
    
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
