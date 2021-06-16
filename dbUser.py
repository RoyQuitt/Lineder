import json

from flask_login import UserMixin
# from datetime import datetime, timezone
import datetime
from datetime import timezone, timedelta
from db import get_db
import dateutil.parser
from freebusy_range import TZ_DELTA
from google.oauth2.credentials import Credentials

"""
The User class has methods to get an existing user from the database and create a new user:
"""


class MyUser(UserMixin):
    def __init__(self, email, name, phone, creds):
        self.id = None
        self.email = email
        self.name = name
        self.phone = phone
        self.creds = creds
        if self.id is None:
            self.id = MyUser.get_id_by_email(self.email)
            if self.id is None:
                self.id = MyUser.create(self.email, name, phone, creds)

    # def set_id(self, new_id):
    #     self.id = new_id
    @staticmethod
    def get_all_creds():
        creds_dict: dict[int: str] = {}
        db = get_db()
        result: list = db.execute(
            "SELECT user_id, creds FROM myUser"
        ).fetchall()
        print("result:", result)
        for user in result:
            creds_dict[user[0]] = user[1]
        return creds_dict

    @staticmethod
    def get_address_by_name(name):
        # this function is not so safe because there could
        # potentially be (though unlikely) two users with the same
        # meaning the function will return the address of the one
        # that appears first in th DB
        db = get_db()
        address = db.execute(
            "SELECT email FROM myUser WHERE real_name = ?", (name,)
        ).fetchone()
        return address[0]

    @staticmethod
    def get_user_name(user_address):
        user_id = MyUser.get_id_by_email(user_address)
        db = get_db()
        name = db.execute(
            "SELECT real_name FROM myUser WHERE user_id = ?", (user_id,)
        ).fetchone()
        return name[0]

    @staticmethod
    def get_user_phone(user_address):
        user_id = MyUser.get_id_by_email(user_address)
        # print(user_address, user_id)
        db = get_db()
        phone = db.execute(
            "SELECT phone FROM myUser WHERE user_id = ?", (user_id,)
        ).fetchone()
        if phone is None:
            return None
        return phone[0]

    @staticmethod
    def get_user_ranges(user_address) -> list[tuple[datetime.datetime, datetime.datetime]]:
        # print("User address in get ranges:", user_address)
        user_id = MyUser.get_id_by_email(user_address)
        db = get_db()
        ranges = db.execute(
            "SELECT * FROM freebusy WHERE owner_id = ?", (user_id,)
        ).fetchall()
        final_ranges: list[tuple[datetime.datetime, datetime.datetime]] = []
        for c_range in ranges:
            start = dateutil.parser.parse(c_range[2])
            end = dateutil.parser.parse(c_range[3])
            temp_range = (start, end)
            final_ranges.append(temp_range)
        return final_ranges

    @staticmethod
    def is_available(user_address, time_to_check=None) -> bool:
        # since default function parameters values are calculated at interpretation time,
        # the default 'time_to_check' value is the time at which the server was ran and
        # and not the time when the function was called.
        # this is a workaround for that, the default value of 'time_to_check' is 'None'
        # if 'time_to_check' is 'None' set it to the current time.
        if time_to_check is None:
            time_to_check = datetime.datetime.now(tz=timezone(timedelta(hours=TZ_DELTA), 'IST'))
        user_ranges: list[tuple] = MyUser.get_user_ranges(user_address)
        is_available = True
        for c_range in user_ranges:
            # current_range: tuple[datetime, datetime] = range
            c_start = c_range[0]  #.isoformat()
            c_end = c_range[1]  #.isoformat()
            print("is:", c_start, time_to_check, c_end)
            if c_start <= time_to_check <= c_end:  # 0 = start, 1 = end
                is_available = False
        return is_available

    @staticmethod
    def next_available(user_address) -> datetime:
        if MyUser.is_available(user_address):
            return datetime.datetime.utcnow().isoformat()  # (now)

        ranges: list[tuple[datetime, datetime]] = MyUser.get_user_ranges(user_address)
        # print("ranges in 'next_available':", ranges)
        ranges_end: list[datetime] = [range[1] for range in ranges]
        ranges_end.sort()
        # print("ranges end:", ranges_end)
        # print(ranges_end)
        # check if first end time in 'ranges_end' is not inside another range
        overlapping: bool = not MyUser.is_available(user_address, time_to_check=ranges_end[0] + timedelta(seconds=1))
        # print("overlapping:", overlapping)
        next_available: datetime = ranges_end[0]
        i = 1
        now = datetime.datetime.now(tz=timezone(timedelta(hours=2), 'IST'))
        while overlapping and i < len(ranges_end):
            # print(ranges_end[i], ranges_end[i] > now)
            if ranges_end[i] > now:
                # print("future")
                overlapping = not MyUser.is_available(user_address, time_to_check=ranges_end[i] + timedelta(seconds=1))
                # print(ranges_end[i], overlapping)
                next_available = ranges_end[i]
            i += 1
        return next_available

    @staticmethod
    def get_id_by_email(email):
        # print("get by id")
        db = get_db()
        # print("User address in get id:", email)
        gotUser = db.execute(
            "SELECT * FROM myUser WHERE email = ?", (email,)
        ).fetchone()
        # print(gotUser, type(gotUser))
        if gotUser is None:
            # print("not in db")
            return None  # not in DB
        user_id = gotUser[0]
        # print(user_id)
        # print("User in get by email:", gotUser[0], gotUser[1])
        return user_id

    # @staticmethod
    # def update_all_events_from_db():
    #     db = get_db()
    #     all_users = db.execute("SELECT * FROM myUser")
    #     for instance in all_users:  # for every instance of the class
    #         MyUser.get_user_events(instance.id)  # get updated events from the db
    #     print("updated all events")

    # def update_user_events(self):
    #     db = get_db()
    #     self.events = db.execute(
    #         "SELECT * FROM events WHERE owner_id = ?", (self.id,)
    #     ).fetchall()
    #     print("updated user events:", self.id + ":", self.events)

    @staticmethod
    def get(user_id):
        db = get_db()
        print("getting user:", user_id)
        user = db.execute(
            "SELECT * FROM myUser WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not user:
            return False

        user = MyUser(
            email=user[2],
            name=user[1],
            phone=user[3],
            creds=user[4]
        )
        user.id = user_id
        return user

    @staticmethod
    def create(email, name, phone, creds):
        db = get_db()
        if type(creds) is str:
            print("creds is str")
            creds_json = creds
        elif type(creds) is not dict:
            print("creds is not dict")
            creds_json = creds.to_json()
        else:
            print("else")
            creds_json = json.dumps(creds, indent=4)
        print("creds type:", type(creds))
        print("creds json type:", type(creds_json))
        print(creds_json)
        db.execute(
            "INSERT INTO myUser (real_name, email, phone, creds) "
            "VALUES (?, ?, ?, ?)",
            (name, email, phone, creds_json),
        )
        db.commit()
        cur = db.cursor()  # cursor to find last rowid
        last_id = cur.lastrowid
        # self.id = last_id  # set 'self.id' to last rowid
        print("\nNEW USER ADDED TO DB!")
        print(name, email, phone, creds)
        return last_id

    @staticmethod
    def update_creds(user_id, creds):
        db = get_db()
        if type(creds) is str:
            print("creds is str")
            creds_json = creds
        elif type(creds) is not dict:
            print("creds is not dict")
            creds_json = creds.to_json()
        else:
            print("else")
            creds_json = json.dumps(creds, indent=4)

        db.execute(
            "UPDATE myUser SET creds = ? WHERE user_id = ?", (creds_json, user_id)
        )
        db.commit()
        print("updated creds")

    def serialize(self):
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone
        }

"""
The code executes SQL statements against the database, which is retrieved from the
get_db() function from the previous db.py file. Each new user results in the insertion of
an additional row in the database.
"""