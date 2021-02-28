class Waiter:
    def __init__(self, name, place, email, phone):
        self.name = name
        self.place = place
        self.email = email
        self.phone = phone

    def serialize(self):
        return {
            'name': self.name,
            'place': self.place,
            'email': self.email,
            'phone': self.phone
        }