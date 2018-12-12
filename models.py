class Account():
    def get_rooms(self, limit, before=0):
        raise NotImplementedError()

    def get_room(self, id):
        raise NotImplementedError()

    def add_room(self, name):
        raise NotImplementedError()


class Client():
    pass


class Room():
    def get_users(self):
        raise NotImplementedError()

    def get_user(self, id):
        raise NotImplementedError()

    def add_user(self, id):
        raise NotImplementedError()

    def remove_user(self, id):
        raise NotImplementedError()

    def send(self, msg):
        raise NotImplementedError()

    def get_messages(self, limit=1000000, before=None):
        raise NotImplementedError()
        


class User():
    def get_name(self):
        raise NotImplementedError()

    def get_nickname(self):
        return get_name()

    def get_color(self):
        raise NotImplementedError()


class Message():
    def get_timestamp(self):
        raise NotImplementedError()

    def get_body(self):
        raise NotImplementedError()

    def get_user(self):
        raise NotImplementedError()
