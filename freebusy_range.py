from flask_login import UserMixin
from datetime import datetime, timezone
from db import get_db
import pandas as pd


class Freebusy(UserMixin):
    def __init__(self, owner_id, start_time, end_time):
        self.id = None
        self.owner_id = owner_id
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def get_user_ranges(owner_id):
        db = get_db()
        ranges = db.execute(
            "SELECT * FROM freebusy WHERE owner_id = ?", (owner_id,)
        ).fetchall()
        if not ranges:
            return None
        return ranges

    @staticmethod
    def get_range(range_id):
        db = get_db()
        range = db.execute(
            "SELECT * FROM freebusy WHERE rowid = ?", (range_id,)
        ).fetchone()
        if not range:
            return None
        return range

    @staticmethod
    def create_range(owner_id, start_time: datetime, end_time: datetime):
        db = get_db()
        ranges = Freebusy.get_user_ranges(owner_id)
        new_range = Freebusy(owner_id, start_time, end_time)
        print(type(new_range), type(ranges))
        if ranges is None or new_range not in ranges:  # if the new range is not in the database
            db.execute(
                "INSERT INTO freebusy (owner_id, start_time, end_time) VALUES (?, ?, ?)",
                (owner_id, start_time, end_time)
            )
            db.commit()
            cur = db.cursor()  # cursor to find last rowid
            last_id = cur.lastrowid
            # start_time.strftime("%m/%d/%Y, %H:%M:%S")
            # end_time.strftime("%m/%d/%Y, %H:%M:%S")
            print("\nADDED NEW RANGE!")
            print(str(owner_id) + ", " + str(start_time) + ", " + str(end_time))
            if not Freebusy.get_range(last_id):  # check if range was created successfully
                return False
            return True
        else:  # range already in database
            return True

    @staticmethod
    def print_table():
        db = get_db()
        print(pd.read_sql_query("SELECT * FROM freebusy", db))

    @staticmethod
    def clean_db():
        db = get_db()
        db.execute(
            "DELETE FROM freebusy"
            "WHERE start_time NOT IN"
            "("
            "SELECT MIN(start_time) start_time"
            "FROM freebusy"
            "GROUP BY start_time, end_time"
            ")"
        )
        db.commit()