class Notification:
    def __init__(self, name, phone, email):
        self.name = name
        self.phone = phone
        self.email = email

    def serialize(self):
        return {
            'name': self.name,
            'phone': self.phone,
            'email': self.email
        }