CREATE TABLE events (
  event_id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  title TEXT,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL
);

/*
YYYY-MM-DDTHH:MM:SS - "2021-01-03T15:15:00Z"
*/