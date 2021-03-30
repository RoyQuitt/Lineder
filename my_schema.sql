CREATE TABLE myUser (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    real_name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    creds TEXT UNIQUE
);


CREATE TABLE freebusy (
    range_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);


CREATE TABLE ques (
    callee_id INTEGER NOT NULL, -- id of the owner of the queue
    waiter_id INTEGER NOT NULL, -- id of the user that is waiting
    place_in_line INTEGER NOT NULL -- the waiter's place in the calle's queue
);

--/*
--YYYY-MM-DDTHH:MM:SS - "2021-01-03T15:15:00Z"
--*/