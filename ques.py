import pandas as pd

from db import get_db
from dbUser import MyUser
from waiter import Waiter
from notification import Notification
import Lineder_logging

my_logger = Lineder_logging.get_logger ('Ques')


class Ques:
    def __init__ (self, callee_id, waiter_id):
        self.id = None
        self.calle_id = callee_id
        self.waiter_id = waiter_id
        self.place_in_line = None

    @staticmethod
    def remove_from_que (callee_address, waiter_address) -> bool:
        """
        Removes the waiter_address from the callee que
        Used when the waiter does not want or should not wait anymore for the callee
        :param callee_address:
        :param waiter_address:
        :return:
        """
        callee_id = MyUser.get_id_by_email (callee_address)
        waiter_id = MyUser.get_id_by_email (waiter_address)
        waiter_place = Ques.get_place_in_line (waiter_id, callee_id)
        db = get_db ()
        db.execute (
            "DELETE from Ques WHERE callee_id = ? AND waiter_id = ?",
            (callee_id, waiter_id)
        )
        if Ques.get_place_in_line (waiter_id, callee_id) is None:
            db.execute (
                "UPDATE ques SET place_in_line = place_in_line - 1"
                " WHERE place_in_line > ? AND callee_id =?",
                (waiter_place, callee_id)
            )
        else:
            return False
        db.commit ()
        return Ques.get_place_in_line (waiter_id, callee_id) is None

    @staticmethod
    def get_my_que (user_address):
        user_id = MyUser.get_id_by_email (user_address)
        db = get_db ()
        que_ids = db.execute (
            "SELECT * FROM ques WHERE callee_id = ?",
            (user_id,)
        ).fetchall ()
        # print(que_ids)
        que: list[Waiter] = []
        for waiter in que_ids:
            c_id = waiter[1]
            c_user = MyUser.get (c_id)
            c_name = c_user.name
            c_address = c_user.email
            c_phone = c_user.phone
            c_waiter = Waiter (
                email=c_address,
                name=c_name,
                phone=c_phone,
                place=waiter[2]
            )
            que.append (c_waiter)
        # print("que:", que)
        # sort 'que' according to the 'place' attribute of waiter
        que.sort (key=lambda x: x.place)
        # print("que:", que)
        return que

    @staticmethod
    def get_notifications (user_address):
        user_id = MyUser.get_id_by_email (user_address)
        db = get_db ()
        notifications_rows = db.execute (
            "SELECT * FROM ques WHERE waiter_id = ? AND place_in_line = 1", (user_id,)
        ).fetchall ()
        notifications: list[Notification] = []
        for notification in notifications_rows:
            callee_id = notification[0]
            callee = MyUser.get (callee_id)
            notifications.append (Notification (callee.name, callee.phone, callee.email))
        # print("notifications:", notifications)
        return notifications

    @staticmethod
    def move_to_top (waiter_address, calle_address):
        waiter_id = MyUser.get_id_by_email (waiter_address)
        callee_id = MyUser.get_id_by_email (calle_address)
        waiter_place = Ques.get_place_in_line (waiter_id, callee_id)
        loop_start = waiter_place - 1
        print ("place:", waiter_place)
        print ("start:", loop_start)
        db = get_db ()
        # loop to go over all the waiters in the que
        # and move each one one place back
        db.execute (
            "UPDATE ques SET place_in_line = place_in_line + 1"
            " WHERE place_in_line < ? AND callee_id =?",
            (waiter_place, callee_id)
        )
        print ("moved down people above")
        Ques.print_table ()
        # move the waiter that needs to be moved to the top to the top
        db.execute (
            "UPDATE ques set place_in_line = 1 WHERE waiter_id = ? AND callee_id = ?",
            (waiter_id, callee_id)
        )
        db.commit ()  # commit to finish transaction
        print ("moved waiter up")
        Ques.print_table ()
        updated_place = Ques.get_place_in_line (waiter_id, callee_id)  # waiter place after change
        if updated_place == 1:  # check if the waiter is actually at the top of the que
            return True
        return False

    @staticmethod
    def get_place_in_line (waiter_id, callee_id):
        db = get_db ()
        place = db.execute (
            "SELECT place_in_line FROM ques WHERE callee_id = ? AND waiter_id = ?",
            (callee_id, waiter_id)
        ).fetchone ()
        if place is None:
            return None
        return place[0]

    @staticmethod
    def get_que_size (owner_id):
        db = get_db ()
        que = db.execute (
            "SELECT place_in_line FROM ques WHERE callee_id = ?", (owner_id,)
        ).fetchall ()
        print ("que:", que)
        for q in que:
            print (q)
        print (len (que))
        if not que:
            return 0
        return len (que)

    @staticmethod
    def get_user_que (owner_address):
        owner_id = MyUser.get_id_by_email (owner_address)
        db = get_db ()
        que = db.execute (
            "SELECT * FROM ques WHERE callee_id = ?", (owner_id,)
        ).fetchall ()
        if not que:
            return None

        return que

    @staticmethod
    def create_que_item (callee_address, waiter_address):
        """
        :param calle_address:
        :param waiter_address:
        :return: if successful - place in line,
                 if not - 0.
        """
        waiter_id = MyUser.get_id_by_email (waiter_address)
        callee_id = MyUser.get_id_by_email (callee_address)
        callee_que = Ques.get_user_que (callee_address)
        # create a list containing all of the id's
        # of the users waiting in the callee's line
        # print("callee_que:", callee_que[0][0], callee_que[0][1], callee_que[0][2])
        if callee_que:
            print ("que alive")
            callee_que_waiter_ids = [item[1] for item in callee_que]
            if waiter_id in callee_que_waiter_ids:
                print ("already in que")
                # return value for "already in the que"
                return Ques.get_place_in_line (waiter_id, callee_id)
            db = get_db ()
            place_in_line = Ques.get_que_size (callee_id) + 1
            db.execute (
                "INSERT INTO ques (callee_id, waiter_id, place_in_line) VALUES (?, ?, ?)",
                (callee_id, waiter_id, place_in_line)
            )
            db.commit ()
        else:
            print ("que dead")
            callee_que_waiter_ids = []
            db = get_db ()
            place_in_line = 1
            db.execute (
                "INSERT INTO ques (callee_id, waiter_id, place_in_line) VALUES (?, ?, ?)",
                (callee_id, waiter_id, place_in_line)
            )
            db.commit ()
        print (callee_que_waiter_ids)
        return place_in_line

    @staticmethod
    def get_que_item (item_id):
        db = get_db ()
        item = db.execute (
            "SELECT * FROM ques WHERE rowid = ?", (item_id,)
        ).fetchone ()
        if not item:
            return None
        return item

    @staticmethod
    def print_table ():
        db = get_db ()
        print (pd.read_sql_query ("SELECT * FROM ques", db))
