from db import get_db
from flask_login import UserMixin
from dbUser import MyUser as DbUser


class MyEvent(UserMixin):
    def __init__(self, event_id, owner_id, title, start, end):
        self.event_id = event_id
        self.owner_id = owner_id
        self.title = title
        self.start = start
        self.end = end

    @staticmethod
    def get_event(event_id):
        db = get_db()
        event = db.execute(
            "SELECT * FROM events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if not event:
            return None

        event = MyEvent(
            event_id=event[0], owner_id=event[1], title=event[2], start=event[3], end=event[4]
        )
        return event

    @staticmethod
    def create(event_id, owner_id, title, start, end):
        new_event = MyEvent(event_id, owner_id, title, start, end)
        db = get_db()
        db.execute(
            "INSERT INTO events (event_id, owner_id, title, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?)",
            (new_event.event_id, new_event.owner_id, new_event.title, new_event.start, new_event.end),
        )
        db.commit()
        print("\nADDED NEW EVENT TO DB!")
        print(new_event)
        DbUser.update_user_events(new_event.owner_id)  # update owner's event list

    def serialize(self):
        """
        This is where the JSON magic happens. This is the dictionary that specifies how to serialized the class.
        :return: A serialized event in the form of a dictionary
        """
        return {
            'title': self.title,
            'start': self.start,
            'end': self.end
        }


