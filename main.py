#!.venv/bin/python3


import curses
import curses.textpad
import fbchat.client
from fbchat.models import Message
import settings
from datetime import datetime, timedelta
from threading import Thread


class Client(fbchat.client.Client):

    user_cache = {}

    def __init__(self, email, password, callback):
        self.callback = callback
        super().__init__(email, password, logging_level=100000)

    def onMessage(self, message_object, thread_id, **kwargs):
        message_object.author = int(message_object.author)
        self.callback(message_object, thread_id)

    def get_user_name(self, uid: int):
        if uid not in self.user_cache:
            users = self.fetchUserInfo(str(uid))
            self.user_cache[uid] = users[str(uid)]
        return self.user_cache[uid].first_name.lower()

    def get_user_color_pair(self, uid: int):
        return curses.color_pair(((uid // 7494) % 66 + 7) % 6 + 2)


class Chat():
    
    def __init__(self, window, thread):
        self.window = window
        self.max_delta = timedelta(minutes=10)
        self.scroll_i = 0
        self.messages = fb.fetchThreadMessages(thread.uid, limit=300)
        self.messages.reverse()
        for m in self.messages:
            m.author = int(m.author)
        self.draw_messages()
        self.thread = thread


    def draw_date(self, d):
        return d.strftime('%h %d, %Y - %H:%M:%S')


    def draw_messages(self):
        if len(self.messages) == 0:
            return
        self.window.clear()
        y, x = self.window.getmaxyx()
        msgs = self.messages[-y - self.scroll_i:]
        msgs.reverse()
        msgs = msgs[self.scroll_i:]
        last_date = datetime.fromtimestamp(int(msgs[0].timestamp) // 1000)
        i = y - 1
        for m in msgs:
            date = datetime.fromtimestamp(int(m.timestamp) // 1000)
            if last_date - date > self.max_delta:
                self.window.addstr(i, 0, self.draw_date(date))
                i -= 1
                if i < 1: break
                i -= 1
                if i < 1: break
            last_date = date
            if m.text != None:
                text = m.text
            else:
                text = str(m.attachments)
            segms = text.split('\n')
            pre_l = len('[HH:MM:SS] <%s> ' % fb.get_user_name(m.author))
            l = x - pre_l - 1
            segms2 = []
            for s in segms:
                if len(s) <= l:
                    segms2.append(s)
                else:
                    for b in  range(0, len(s), l):
                        segms2.append(s[b:b+l])
            segms = segms2
            segms.reverse()
            for j,segm in enumerate(segms):
                self.window.addstr(i, pre_l, segm[:l])
                i -= 1
                if i < 1: break
            tup = ('[%s] <' % date.strftime("%H:%M:%S"), fb.get_user_name(m.author))
            self.window.addstr(i + 1, 0, tup[0])
            self.window.addstr(tup[1], fb.get_user_color_pair(m.author))
            self.window.addstr('> ')
            if i < 1: break
        self.window.addstr(i, 0, self.draw_date(last_date))
        self.window.refresh()


    def add_message(self, msg):
        self.messages.append(msg)
        self.draw_messages()


    def scroll(self, i):
        self.scroll_i += i
        y, x = self.window.getmaxyx()
        if self.scroll_i < 0:
            self.scroll_i = 0
        elif self.scroll_i >= len(self.messages) - 1:
            self.scroll_i = len(self.messages) - 1
        self.draw_messages()


def main(screen):
    global fb

    for i in range(2,8):
        curses.init_pair(i, i, curses.COLOR_BLACK)


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

    def callback(msg, thread_id):
        chat.add_message(msg)

    fb = Client(settings.EMAIL, settings.PASSWORD, callback)
    threads = fb.fetchThreadList()
    curr_thread = threads[0]

    chat = Chat(chatwin, curr_thread)

    chatwin_i = 0
    write_str = []

    Thread(target=fb.listen, daemon=True).start()

    y, x = threadswin.getmaxyx()
    while len(threads) < y:
        ts = int(threads[-1].last_message_timestamp) - 1
        tl = fb.fetchThreadList(before=ts)
        for t in tl:
            threads.append(t)
        if len(tl) == 0: break

    seen = set()
    threads = [x for x in threads if not (x.uid in seen or seen.add(x.uid))]
    
    def draw_threads_list(selected_thread):
        y, x = threadswin.getmaxyx()
        i = 0
        for t in threads:
            threadswin.addstr(i, 0, t.name if t.name else '<None>', curses.A_REVERSE if t.uid == selected_thread.uid else curses.A_NORMAL)
            i += 1
            if i >= y: break
        threadswin.refresh()
    draw_threads_list(curr_thread)

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
            fb.send(Message(text=''.join(write_str)), thread_id=curr_thread.uid, thread_type=curr_thread.type)
            writewin.clear()
            write_str.clear()
        elif ch == ord('\t'):
            # Switch threads
            i = threads.index(curr_thread)
            while True:
                ch = writewin.getch()
                if ch == curses.KEY_DOWN:
                    i += 1
                    if i >= len(threads):
                        i = len(threads) - 1
                    draw_threads_list(threads[i])
                elif ch == curses.KEY_UP:
                    i -= 1
                    if i < 0:
                        i = 0
                    draw_threads_list(threads[i])
                elif ch == ord('\n'):
                    curr_thread = threads[i]
                    chat = Chat(chat.window, curr_thread)
                    break
                elif ch == ord('\t'):
                    draw_threads_list(curr_thread)
                    break
        else:
            write_str.append(chr(ch))
            writewin.addch(ch)


curses.wrapper(main)
