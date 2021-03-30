from flask_login import UserMixin
from db import get_db
import json
from google.oauth2.credentials import Credentials
from quickstart import Quickstart
from dbUser import MyUser as DbUser
from freebusy_range import Freebusy as Range


class RefreshRanges(UserMixin):
    def __init__(self):
        # self.db = get_db()
        self.creds_dict: dict[int: str] = {}
        self.all_creds: dict[int: Credentials] = {}
        self.all_ranges: list = []
        self.get_all_creds()
        self.convert_all_jsons_to_creds()

    def refresh_all_ranges(self):
        if self.all_creds is not None:
            for user_id, user_creds in self.all_creds.items():
                print("refreshing...")
                # print("user_id:", user_id)
                # print("user_creds:", user_creds)
                self.refresh_one_user_ranges(user_id, user_creds)

    @staticmethod
    def refresh_one_user_ranges(user_id, user_creds):
        # user_creds: dict[int: Credentials] = self.get_user_creds(user_id)
        # print("creating quickstart instance")
        current_quickstart_instance = Quickstart()
        # print("making the requests")
        freebusy, user_address, name, phone, user_credentials = \
            current_quickstart_instance.make_requests(given_creds=user_creds)
        # print("done")
        # print(freebusy)
        # cur_user = DbUser(user_address, name, phone, user_credentials)
        # user_id = DbUser.get_id_by_email(user_address)

        # Clear all of the "old" ranges the user currently has
        Range.delete_user_ranges(user_id)

        # Create the new ranges in our database
        for c_range in freebusy:
            Range.create_range(user_id, c_range['start'], c_range['end'])

    def get_user_creds(self, user_id) -> dict[int: Credentials]:
        return self.all_creds[user_id]

    def convert_all_jsons_to_creds(self):
        for user_id in self.creds_dict:
            current_user_creds_string = self.creds_dict[user_id]
            current_user_creds_dict = json.loads(current_user_creds_string)
            self.all_creds[user_id] = Credentials.from_authorized_user_info(current_user_creds_dict)

    # def get_all_ranges(self):
    #     db = get_db()
    #     result = db.execute(
    #         "SELECT * FROM freebusy"
    #     ).fetchall()
    #     self.all_ranges = [range_instance[0] for range_instance in result]

    def get_all_creds(self):
        self.creds_dict = DbUser.get_all_creds()
        # db = get_db()
        # # creds_dict: dict[int: str] = {}
        # result: list = db.execute(
        #     "SELECT user_id, creds FROM myUser"
        # ).fetchall()
        # print("result:", result)
        # for user in result:
        #     self.creds_dict[user[0]] = user[1]
        # print("creds_dict:", self.creds_dict)
