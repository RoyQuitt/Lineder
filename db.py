# http://flask.pocoo.org/docs/1.0/tutorial/database/
import sqlite3

# import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    return sqlite3.connect(
            "sqlite_db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
    # if "db" not in g:
    #     g.db = sqlite3.connect(
    #         "sqlite_db", detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
    #     )
    #     g.db.row_factory = sqlite3.Row
    #
    # return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


# @with_appcontext
def init_db():
    db = get_db()

    # with current_app.open_resource("my_schema.sql") as f:
    #     db.executescript(f.read().decode("utf8"))


# @click.command("init-db")
# @with_appcontext
# def init_db_command():
#     """Clear the existing data and create new tables."""
#     print("g:", g)
#     init_db()
#     # print("Initialized the database.")
#     # click.echo("Initialized the database.")
#     print("Initialized the database.")


# def init_app(app):
#     app.teardown_appcontext(close_db)
#     app.cli.add_command(init_db_command)
