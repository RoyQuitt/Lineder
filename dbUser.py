from flask_login import UserMixin
# from datetime import datetime, timezone
import datetime
from datetime import timezone, timedelta
from db import get_db
import dateutil.parser

"""
The User class has methods to get an existing user from the database and create a new user:
"""


class MyUser(UserMixin):
    def __init__(self, email, name, phone):
        self.id = None
        self.email = email
        self.name = name
        self.phone = phone
        if self.id is None:
            self.id = MyUser.get_id_by_email(self.email)
            if self.id is None:
                self.id = MyUser.create(self.email, name, phone)

    def set_id(self, new_id):
        self.id = new_id

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
        db = get_db()
        phone = db.execute(
            "SELECT phone FROM myUser WHERE user_id = ?", (user_id,)
        ).fetchone()
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
    def is_available(user_address, time=(datetime.datetime.now(tz=timezone(timedelta(hours=2), 'IST')))) -> bool:
        user_ranges: list[tuple] = MyUser.get_user_ranges(user_address)
        is_available = True
        for c_range in user_ranges:
            # current_range: tuple[datetime, datetime] = range
            c_start = c_range[0]  #.isoformat()
            c_end = c_range[1]  #.isoformat()
            # c_start = datetime.datetime.fromisoformat(c_range[0])
            # c_end = datetime.datetime.fromisoformat(c_range[1])
            # if c_start < c_end:
            #     print("start is smaller than end")
            # print(type(c_range[0]), type(c_range[1]))
            # print(type(c_start), type(time), type(c_end))
            # print(c_start, time, c_end)
            print(c_start, time, c_end)
            if c_start < time < c_end:  # 0 = start, 1 = end
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
        # print(ranges_end)
        # check if first end time in 'ranges_end' is not inside another range
        overlapping: bool = not MyUser.is_available(user_address, time=ranges_end[0])
        next_available: datetime = ranges_end[0]
        i = 1
        while overlapping and i < len(ranges_end):
            overlapping = MyUser.is_available(user_address, time=ranges_end[i])
            next_available = ranges_end[i]
            i += 1
        return next_available

    @staticmethod
    def get_id_by_email(email):
        db = get_db()
        # print("User address in get id:", email)
        gotUser = db.execute(
            "SELECT * FROM myUser WHERE email = ?", (email,)
        ).fetchone()
        # print(gotUser, type(gotUser))
        if gotUser is None:
            return None  # not in DB
        user_id = gotUser[0]
        # print("User in get by email:", gotUser[0], gotUser[1])
        return user_id

    @staticmethod
    def update_all_events_from_db():
        db = get_db()
        all_users = db.execute("SELECT * FROM myUser")
        for instance in all_users:  # for every instance of the class
            MyUser.get_user_events(instance.id)  # get updated events from the db
        print("updated all events")

    def update_user_events(self):
        db = get_db()
        self.events = db.execute(
            "SELECT * FROM events WHERE owner_id = ?", (self.id,)
        ).fetchall()
        print("updated user events:", self.id + ":", self.events)

    @staticmethod
    def get_user_events(user_id):
        db = get_db()
        return db.execute(
            "SELECT * FROM events WHERE owner_id = ?", (user_id,)
        ).fetchall()

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
            phone=user[3]
        )
        user.id = user_id
        return user

    @staticmethod
    def create(email, name, phone):
        db = get_db()
        db.execute(
            "INSERT INTO myUser (real_name, email, phone) "
            "VALUES (?, ?, ?)",
            (name, email, phone),
        )
        db.commit()
        cur = db.cursor()  # cursor to find last rowid
        last_id = cur.lastrowid
        # self.id = last_id  # set 'self.id' to last rowid
        print("\nNEW USER ADDED TO DB!")
        print(name, email, phone)
        return last_id

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