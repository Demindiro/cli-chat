#!.venv/bin/python3


import fbchat.client
from fbchat.models import Message, Group, User
import models
import chat
from datetime import datetime
from threading import Thread

users = {}

class Client(fbchat.client.Client):

    rooms = None

    def __init__(self, email, password):
        chat.log('Logging in as ' + email + '...')
        super().__init__(email, password, logging_level=100000)
        chat.log('Success!')
        self.listend = Thread(target=self.listen, daemon=True)
        self.listend.start()

    def get_rooms(self, limit=20, before=0):
        if self.rooms == None:
            chat.log('Getting rooms...')
            threads    = self.fetchThreadList()
            self.rooms = {t.uid: Room(self, t) for t in threads}
            chat.log('Done')
        return self.rooms

    def get_room(self, id):
        return self.rooms[id]

    def onMessage(self, message_object, thread_id, **kwargs):
        if self.rooms == None:
            self.get_rooms()
        if thread_id not in self.rooms:
            chat.log('4')
            t = self.fetchThreadInfo(thread_id)
            for k,v in t.items:
                self.rooms[k] = Room(self, v)
        self.rooms[thread_id].add_message(Message(message_object))

    def onListenError(self, exception):
        chat.log(repr(exception))

    def onMessageError(self, exception, msg, **kwargs):
        self.onListenError(exception)


class Room(models.Room):

    msgs = None

    def __init__(self, client, thread):
        self.client = client
        self.name   = thread.name if thread.name != None else '<None>'
        if type(thread) == User:
            self.users = [thread]
        else:
            self.users = client.fetchUserInfo(*thread.participants)
        self.thread = thread
        self.id     = thread.uid

    def get_user(self, id):
        return self.users[id]

    def get_users(self):
        return self.users

    def get_messages(self, limit=100000, before=None):
        if self.msgs == None:
            msgs = self.client.fetchThreadMessages(self.thread.uid)
            self.msgs = [Message(m) for m in msgs]
            self.msgs.reverse()
        return self.msgs 

    def send(self, text):
        self.client.send(fbchat.models.Message(text=text), thread_id=self.thread.uid, thread_type=self.thread.type)

    def add_message(self, msg):
        if self.msgs == None:
            get_messages()
        self.msgs.append(msg)
        if self.win:
            self.win.add_message(msg)
            self.win.render()
        
    def link_window(self, win):
        self.win = win
        for m in self.msgs:
            win.add_message(m)
        win.render()

class Message(models.Message):

    def __init__(self, msg):
        self.msg = msg
    
    def get_timestamp(self):
        return datetime.fromtimestamp(int(self.msg.timestamp) // 1000)

    def get_body(self):
        return self.msg.text if self.msg.text else repr(self.msg.attachments)

    def get_user(self):
        if self.msg.author not in users:
            d = _client.fetchUserInfo(self.msg.author)
            for k,v in d.items():
                users[k] = v
        return users[self.msg.author].first_name.lower()


class Account(models.Account):

    _client = None

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def get_client(self):
        global _client
        if self._client == None:
            self._client = Client(self.email, self.password)
            _client = self._client
        return self._client

    def serialize(self):
        return [self.email, self.password]

    def deserialize(obj):
        return Account(obj[0], obj[1])
