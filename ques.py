from db import get_db
import pandas as pd
from dbUser import MyUser


class Ques:
    def __init__(self, callee_id, waiter_id):
        self.id = None
        self.calle_id = callee_id
        self.waiter_id = waiter_id
        self.place_in_line = None

    @staticmethod
    def get_notifications(user_address):
        user_id = MyUser.get_id_by_email(user_address)
        db = get_db()
        notifications = db.execute(
            "SELECT * FROM ques WHERE waiter_id = ? AND place_in_line = ?", (user_id, 1)
        ).fetchall()
        return notifications

    @staticmethod
    def move_to_top(waiter_address, calle_address):
        waiter_id = MyUser.get_id_by_email(waiter_address)
        callee_id = MyUser.get_id_by_email(calle_address)
        waiter_place = Ques.get_place_in_line(waiter_id, callee_id)
        loop_start = waiter_place - 1
        db = get_db()
        # loop to go over all the waiters in the que
        # and move each one one place back
        for place in range(loop_start, 1):
            db.execute(
                "UPDATE ques set place_in_line = ? WHERE place_in_line = ? AND callee_id = ?",
                (place + 1, place, callee_id)
            )
        # move the waiter that needs to be moved to the top to the top
        db.execute(
            "UPDATE ques set place_in_line = 1 WHERE waiter_id = ? AND callee_id = ?",
            (waiter_id, callee_id)
        )
        db.commit()  # commit to finish transaction
        updated_place = Ques.get_place_in_line(waiter_id, callee_id)  # waiter place after change
        if updated_place == 1:  # check if the waiter is actually at the top of the que
            return True
        return False

    @staticmethod
    def get_place_in_line(waiter_id, callee_id):
        db = get_db()
        place = db.execute(
            "SELECT place_in_line FROM ques WHERE callee_id = ? AND waiter_id = ?",
            (callee_id, waiter_id)
        ).fetchone()
        return place

    @staticmethod
    def get_que_size(owner_id):
        db = get_db()
        que = db.execute(
            "SELECT place_in_line FROM ques WHERE calle_id = ?", (owner_id,)
        ).fetchall()
        if not que:
            return 0
        return len(que) + 1

    @staticmethod
    def get_user_que(owner_address):
        owner_id = MyUser.get_id_by_email(owner_address)
        db = get_db()
        que = db.execute(
            "SELECT * FROM que WHERE callee_id = ?", (owner_id,)
        ).fetchall()
        if not que:
            return None
        return que   

    @staticmethod
    def create_que_item(callee_address, waiter_address):
        """
        :param calle_address:
        :param waiter_address:
        :return: if successful - place in line,
                 if not - 0.
        """
        waiter_id = MyUser.get_id_by_email(waiter_address)
        callee_id = MyUser.get_id_by_email(callee_address)
        callee_que = Ques.get_user_que(callee_address)
        # create a list containing all of the id's
        # of the users waiting in the callee's line
        callee_que_waiter_ids = [item[1] for item in callee_que]
        if waiter_id in callee_que_waiter_ids:
            return 0  # return value for "already in the que"
        db = get_db()
        place_in_line = Ques.get_que_size(callee_id) + 1
        db.execute(
            "INSERT INTO ques (calle_id, waiter_id, place_in_line) VALUES (?, ?, ?)",
            (callee_id, waiter_id, place_in_line)
        )
        db.commit()
        return place_in_line

    @staticmethod
    def get_que_item(item_id):
        db = get_db()
        item = db.execute(
            "SELECT * FROM ques WHERE rowid = ?", (item_id,)
        ).fetchone()
        if not item:
            return None
        return item

    @staticmethod
    def print_table():
        db = get_db()
        print(pd.read_sql_query("SELECT * FROM ques", db))