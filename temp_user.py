class TempUser:
    def __init__(self, name: str, address: str, phone: str,
                 pic_url: str, freebusy, headers):
        self.name = name
        self.address = address
        self.phone = phone
        self.pic_url = pic_url
        self.freebusy = freebusy
        self.headers = headers

    def __repr__(self) -> str:
        return "\nName: " + self.name + "\nAddress: " + self.address + \
               "\nPhone: " + self.phone + "\nPic: " + self.pic_url + \
               "\nFreebusy: " + self.freebusy + "\nHeaders: " + self.headers
