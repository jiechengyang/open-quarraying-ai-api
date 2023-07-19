# !/usr/bin/env python3

# -*- coding:utf-8 -*-

__author__ = 'yang yang'

import os
import sys
import logging
import time
import subprocess
import re
import socket
from config.bapp import configs
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

command = ['echo', 'ok']
process = None


def isFunction(obj):
    if callable(obj) and hasattr(obj, '__call__'):
        return True
    return False


def log(s):
    logging.info('[Monitor] %s' % s)


def match_ignore_dir_py_pattern(dir, src_path):
    pattern = r'.*' + dir + '[\\/]?.*\.py'
    return re.match(pattern, src_path) is not None


class CustomFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, fn) -> None:
        # super(CustomFileSystemEventHandler, self).__init__()
        super().__init__()
        self.restart = fn

    def on_any_event(self, event):
        conditions = [
            event.src_path.find('.git') == -1,
            not match_ignore_dir_py_pattern('migration', event.src_path),
            not match_ignore_dir_py_pattern('tests', event.src_path),
            not event.src_path.endswith('pymonitor.py'),
            not event.src_path.endswith('migrate.py'),
            not event.src_path.endswith('make_ai_app.py'),
            event.src_path.endswith('.py')
        ]
        # event.src_path.find('.git') == -1 and not match_ignore_dir_py_pattern('migration', event.src_path) and not match_ignore_dir_py_pattern('tests', event.src_path) and not event.src_path.endswith('pymonitor.py') and not event.src_path.endswith('make_ai_app.py') and event.src_path.endswith('.py')
        if all(conditions):
            log('Python source file changed: %s' % event.src_path)
            if isFunction(self.restart):
                self.restart()
        return super().on_any_event(event)


def restart_process():
    kill_process()
    start_process()


def kill_process():
    global process
    if process:
        log('kill process [%s]...' % process.pid)
        process.kill()
        process.wait()
        log('Process ended with code %s.' % process.returncode)
        process = None


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except OSError:
            return True


def start_process():
    global process, command
    log('Start process %s ...' % command)
    process = subprocess.Popen(
        command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def start_watch(path):
    observer = Observer()
    observer.schedule(event_handler=CustomFileSystemEventHandler(
        restart_process), path=path, recursive=True)
    observer.start()
    log('Start watch %s ...' % path)
    if not is_port_in_use(configs.port):
        start_process()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file = sys.argv[1] if len(sys.argv) > 1 else None
    is_win32 = sys.platform == "win32"
    if not file:
        if is_win32:
            print('Usage: your_python ./pymonitor.py ./your-script.py')
        else:
            print('Usage: ./pymonitor.py your-script.py')
        exit(0)
    path = os.path.abspath('.')
    script = file.replace(".\\", '')
    command = [sys.executable, f'{path}{os.sep}{script}']
    start_watch(path)
