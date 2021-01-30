CREATE TABLE myUser (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE
);

CREATE TABLE myEvent (
  event_id TEXT PRIMARY KEY,
  owner_id INTEGER NOT NULL,
  title TEXT,
  start_time timestamp NOT NULL,
  end_time timestamp NOT NULL
);

CREATE TABLE freebusy (
    owner_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
)

/*
YYYY-MM-DDTHH:MM:SS - "2021-01-03T15:15:00Z"
*/