from ast import literal_eval
from datetime import datetime, timedelta
from threading import Thread
import os
from importlib import import_module
import shlex
import curses
import curses.textpad

import fbchat.client
from fbchat.models import Message

import models


ACCOUNTS_CONF = 'accounts.conf'


class MainMenuRoom(models.Room):

    msgs = []
    name = 'Main Menu'

    def send(self, msg):
        self.msgs.append(msg)
    def get_messages(self, limit=1309483, before=None):
        return self.msgs
    def link_window(self, win):
        self.win = win
        for m in self.msgs:
            win.add_message(m)
        win.render()


class MainMenuMessage(models.Message):
    def __init__(self, s):
        self.msg  = s
        self.time = datetime.now()
        self.user = 'Log'

    def get_timestamp(self):
        return self.time

    def get_body(self):
        return self.msg

    def get_user(self):
        return self.user


class MainMenuClient(models.Client):

    def __init__(self):
        self.rooms = {'Main Menu': MainMenuRoom()}

    def get_rooms(self):
        return self.rooms


class MainMenuAccount(models.Account):

    def __init__(self):
        self.client = MainMenuClient()

    def get_client(self):
        return self.client


class ChatWindow():

    lines = []
    offset = 0

    def __init__(self, window, room):
        self.win  = window
        self.room = room
        self.render()

    def render(self):
        self.lines = []
        for m in self.room.get_messages(self):
            self.add_message(m)
        self.win.clear()
        y, x = self.win.getmaxyx()
        for i,l in enumerate(self.lines[-y:]):
            self.win.addstr(i, 0, l)
        self.win.refresh()

    def add_message(self, msg):
        y, x = self.win.getmaxyx()
        s = f'[{msg.get_timestamp().strftime("%H:%M:%S")}] <{msg.get_user()}> ' +  msg.get_body().replace("\n", " ")
        for l in [s[i:i+x] for i in range(0, len(s), x)]:
            self.lines.append(l)

    def scroll(self, n):
        self.offset += n
        if self.offset < 0:
            self.offset = 0
        self.render()


class RoomsWindow():

    current_account_name = None
    current_room_id      = None
    
    def __init__(self, window):
        self.win = window
        self.render()

    def render(self):
        self.win.clear()
        y, x = self.win.getmaxyx()
        i = 0
        for name in accounts:
            if name in clients:
                color = curses.color_pair(COLOR_ACCOUNT_CONNECTED)
            else:
                color = curses.color_pair(COLOR_ACCOUNT_DISCONNECTED)
            if self.current_account_name == name:
                color |= curses.A_REVERSE
            self.win.addstr(i, 0, name, color | curses.A_BOLD)
            i += 1
            if i >= y: break
            continue
            if name in clients:
                for t in clients[name].get_threads():
                    threadswin.addstr(i, 0, t.name if t.name else '<None>', curses.A_REVERSE if t.uid == selected_thread.uid else curses.A_NORMAL)
                    i += 1
                    if i >= y: break
        self.win.refresh()

    def select(self):
        old_room_id = self.current_room_id
        old_account_name = self.current_account_name
        accs = [a for a in accounts]
        i = 0 #accs.index(self.current_account_name)
        self.current_account_name = accs[i]
        self.current_room_id = None

        while True:
            self.render()
            ch = self.win.getch()
            if ch == ord('\033'):
                ch = self.win.getch()
                if ch != ord('['):
                    log('Unexpected ch: ' + str(ch) + f"('{chr(ch)}')")
                    continue
                ch = self.win.getch()
                if ch == ord('B'):
                    i += 1
                    if i >= len(accs):
                        i = len(accs) - 1
                elif ch == ord('A'):
                    i -= 1
                    if i < 0:
                        i = 0

            elif ch == ord('\n'):
                if not accs[i] in clients:
                    clients[accs[i]] = accounts[accs[i]].get_client()
                rooms      = clients[accs[i]].get_rooms() 
                rooms_list = [r for r in rooms]
                j = 0
                while True:
                    self.win.clear()
                    for k,r in enumerate(rooms_list):
                        self.win.addstr(k, 0, rooms[rooms_list[k]].name, curses.A_REVERSE if k == j else 0)
                    self.win.refresh()
                    ch = self.win.getch()

                    if ch == ord('\033'):
                        ch = self.win.getch()
                        if ch != ord('['):
                            log('Unexpected ch: ' + str(ch) + f"('{chr(ch)}')")
                            continue
                        ch = self.win.getch()
                        if ch == ord('B'):
                            j += 1
                            if j >= len(rooms_list):
                                j = len(rooms_list) - 1
                        elif ch == ord('A'):
                            j -= 1
                            if j < 0:
                                j = 0
                    elif ch == ord('\n'):
                        global chat
                        chat = ChatWindow(chat.win, rooms[rooms_list[j]])
                        rooms[rooms_list[j]].link_window(chat)
                        chat.render()
                        return
                    elif ch == ord('\t'):
                        break
                    else:
                        log(str(ch))
                    self.current_room_id = rooms[rooms_list[j]].id

            elif ch == ord('\t'):
                self.current_account_name = old_account_name
                self.current_room_id = old_room_id
                break
            self.current_account_name = accs[i]
        self.render()


modules  = {}
main_menu_account = MainMenuAccount()
main_menu_room    = main_menu_account.get_client().get_rooms()['Main Menu']
accounts = {'Main Menu': main_menu_account}
clients  = {'Main Menu': main_menu_account.get_client()}


def load_modules(screen):
    i = 0
    screen.clear()
    for m in os.listdir('modules'):
        if m[-3:] == '.py':
            screen.addstr(i, 0, f'Importing {m[:-3]}...')
            screen.refresh()
            modules[m[:-3]] = import_module('modules.' + m[:-3])


def load_accounts():
    if not os.path.exists(ACCOUNTS_CONF):
        with open(ACCOUNTS_CONF, 'w'):
            pass
    else:
        with open(ACCOUNTS_CONF, 'r') as f:
            while True:
                s = f.readline()
                while s == '\n':
                    s = f.readline()
                if s == '':
                    break
                name = s[:-1]
                module = f.readline()[:-1]
                accounts[name] = modules[module].Account.deserialize(literal_eval(f.readline()))


def parse_command(cmd):
    args = shlex.split(cmd)
    if args[0] == 'account':
        if args[1] == 'add':
            accounts[args[2]] = modules[args[3]].Account(*args[4:])
            with open(ACCOUNTS_CONF, 'a') as f:
                f.write(args[2] + '\n' + args[3] + '\n' + repr(accounts[args[2]].serialize()))
    elif args[0] == 'connect':
        try:
            acc = accounts[args[1]]
        except KeyError:
            log(f"Account '{args[1]}' does not exist")
            return
        client[args[1]] = account.connect()
    else:
        log(f"Invalid command '{args[0]}'")
        

def log(s):
    main_menu_room.send(MainMenuMessage(s))
    chat.render()


COLOR_ACCOUNT_CONNECTED    = 101
COLOR_ACCOUNT_DISCONNECTED = 102
COLOR_ACCOUNT_ERROR        = 103

def main(screen):

    global chat

    for i in range(2,8):
        curses.init_pair(i, i, curses.COLOR_BLACK)
    curses.init_pair(COLOR_ACCOUNT_CONNECTED   , curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(COLOR_ACCOUNT_DISCONNECTED, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(COLOR_ACCOUNT_ERROR       , curses.COLOR_RED  , curses.COLOR_BLACK)

    load_modules(screen)
    load_accounts()

    CHAT_X_POS = 44
    screen.clear()
    threadswin = curses.newwin(curses.LINES, CHAT_X_POS - 3,  0, 0)
    chatwin    = curses.newwin(curses.LINES - 2, curses.COLS - CHAT_X_POS, 0, CHAT_X_POS)
    writewin   = curses.newwin(1, curses.COLS, curses.LINES - 1, CHAT_X_POS)
    writebox   = curses.textpad.Textbox(writewin)
    screen.vline(0, CHAT_X_POS - 2, '|', curses.LINES)
    screen.addch(curses.LINES - 2, CHAT_X_POS - 2, ord('+')) 
    screen.hline(curses.LINES - 2, CHAT_X_POS - 1, '-', curses.COLS - CHAT_X_POS)
    screen.refresh()

    main_menu_chat = ChatWindow(chatwin, main_menu_room)
    chat = main_menu_chat
    rooms_list = RoomsWindow(threadswin)
    
    y, x = threadswin.getmaxyx()

    write_str = []
    while True:
        writewin.refresh()
        ch = writewin.getch()
        if ch == curses.KEY_UP:
            chat.scroll(1)
        elif ch == curses.KEY_DOWN:
            chat.scroll(-1)
        elif ch == curses.KEY_BACKSPACE or ch == curses.ascii.BS or ch == curses.ascii.DEL:
            if len(write_str) > 0:
                write_str.pop()
                writewin.delch(0, len(write_str))
        elif ch == ord('\n'):
            if len(write_str) == 0:
                continue
            if write_str[0] == '/':
                parse_command(''.join(write_str[1:]))
            else:
                chat.room.send(''.join(write_str))
            writewin.clear()
            write_str.clear()
        elif ch == ord('\t'):
            rooms_list.select()
        else:
            write_str.append(chr(ch))
            writewin.addch(ch)
