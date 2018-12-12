#!.venv/bin/python3

import chat
import curses

if __name__ == '__main__':
    curses.wrapper(chat.main)
