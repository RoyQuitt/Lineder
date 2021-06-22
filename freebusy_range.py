import time

from flask_login import UserMixin
from datetime import datetime, timezone, timedelta
import pandas as pd

from db import get_db
import Lineder_logging

# constants
TZ_DELTA = 3  # The delta of our time zone from GMT
LOCAL_TIME_ZONE = 'IST'
API_DELAY = 1

my_logger = Lineder_logging.get_logger('Ranges')


# Freebusy as in interface only class to access the FreeBusy ranges of users,
# therefore all of the methods are static
class Freebusy(UserMixin):
    def __init__(self, owner_id, start_time, end_time):
        self.id = None
        self.owner_id = owner_id
        self.start_time = start_time
        self.end_time = end_time

    @staticmethod
    def delete_user_ranges(owner_id):
        db = get_db()
        db.execute(
            "DELETE from freebusy WHERE owner_id = ?", (owner_id,)
        )

    @staticmethod
    def get_user_ranges(owner_id):
        """
        Returns the ranges of a specific user.
        :param owner_id: The ID of the user to retrieve
        :return: the ranges found, if any
        """
        db = get_db()
        ranges = db.execute(
            "SELECT * FROM freebusy WHERE owner_id = ?", (owner_id,)
        ).fetchall()
        if not ranges:
            return None
        return ranges

    @staticmethod
    def get_range(range_id):
        """
        Returns the details of a range by range ID
        :param range_id: the ID of the range to query
        :return: the range instance
        """
        db = get_db()
        rng = db.execute(
            "SELECT * FROM freebusy WHERE rowid = ?", (range_id,)
        ).fetchone()
        if not rng:
            return None
        return rng

    @staticmethod
    def busy_for(owner_id, hours: int, mins: int) -> bool:
        """
        Sets the user to be busy for a specific period of time
        :param owner_id: the ID of the user to set to busy for hours:mins
        :param hours: the hours component
        :param mins: the minutes coponent
        :return: bool
        """
        hours = int(hours)
        mins = int(mins)
        # now = datetime.utcnow()
        now = datetime.now(tz=timezone(timedelta(hours=TZ_DELTA), LOCAL_TIME_ZONE))
        # now = datetime.now(tz=timezone(timedelta(hours=hours)))
        end = now + timedelta(hours=hours, minutes=mins)
        success = Freebusy.create_range(owner_id, now, end)
        my_logger.debug("%s, %s, %s", now, end, success)
        return success

    @staticmethod
    def create_range(owner_id, start_time: datetime, end_time: datetime):
        """
        Adds the range into the database, if it does not exist.
        :param owner_id: the ID of the owner
        :param start_time: Beginning of the range
        :param end_time: End of the range
        :return: always returns TRUE
        """
        db = get_db()
        ranges = Freebusy.get_user_ranges(owner_id)
        new_range = Freebusy(owner_id, start_time, end_time)
        print(type(new_range), type(ranges))

        if ranges is None or new_range not in ranges:  # if the new range is not in the database or we do not have
            # any ranges

            # Insert the record into the freebusy table
            db.execute(
                "INSERT INTO freebusy (owner_id, start_time, end_time)"
                "SELECT ?, ?, ?"
                "WHERE NOT EXISTS (SELECT * FROM freebusy WHERE owner_id = ? AND (start_time = ? OR end_time = ?))"
                , (owner_id, start_time, end_time, owner_id, start_time, end_time)
            )
            db.commit()

            cur = db.cursor()  # cursor to find last rowid
            db.close()
            my_logger.debug("\nADDED NEW RANGE!")
            my_logger.debug("%s, %s, %s", str(owner_id), str(start_time), str(end_time))

            my_logger.debug("Create range returning 'True'")
            return True
        else:  # range already in database
            my_logger.debug("Create range returning 'True' from else section")
            return True
        # TODO:
        # should this function always return TRUE?
        # handle DB error or exception (maybe return FALSE in this case)

    @staticmethod
    def print_table():
        """
        Logs the content of the freebusy table for debugging purposes
        """
        database = get_db()
        my_logger.debug(pd.read_sql_query("SELECT * FROM freebusy", database))
