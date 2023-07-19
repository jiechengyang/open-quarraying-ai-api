#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
Deployment toolkit.
'''

import os
import re

from datetime import datetime
from fabric import Connection, Config
from invoke import FailingResponder

host = '192.168.0.1'
port = 22222
user = 'root'
password = 'root'

db_user = 'root'
db_password = 'root'
db_name = 'quarrying_ai'

_TMP_PATH = '/ddd'
_TAR_FILE = 'dist-quarrying_ai.tar.gz'

_REMOTE_TMP_TAR = '%s/%s' % (_TMP_PATH, _TAR_FILE)

_REMOTE_BASE_DIR = '/aaa'


def _current_path():
    return os.path.abspath('.')


def _now():
    return datetime.now().strftime('%y-%m-%d_%H.%M.%S')


def backup():
    '''
        Dump entire database on server and backup to local.
    '''
    global conn
    dt = _now()
    f = 'backup-%s-%s.sql' % (db_name, dt)
    with conn.cd(_TMP_PATH):
        conn.run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick %s > %s' %
                 (db_user, db_password, db_name, f))
        conn.run('tar -czvf %s.tar.gz %s' % (f, f))
        conn.get('%s.tar.gz' % f, '%s/backup/' % _current_path())
        conn.run('rm -f %s' % f)
        conn.run('rm -f %s.tar.gz' % f)


def build():
    '''
    Build dist package.
    '''
    global conn
    includes = ['public', 'backup', 'components', 'config',
                'insectid', 'khandy', 'plantid', 'queue_job', '*.py']
    excludes = ['public/.DS_Store', 'public/uploads/task', 'public/uploads/task_result', 'public/uploads/.DS_Store', 'dist', 'test', '*.pyc', '*.pyo',
                '.vscode', 'private', 'fabfile.py']
    conn.local('rm -f dist/%s' % _TAR_FILE)
    with conn.cd(_current_path()):
        cmd = ['tar', '--dereference', '-czvf', 'dist/%s' % _TAR_FILE]
        cmd.extend(['--exclude=\'%s\'' % ex for ex in excludes])
        cmd.extend(includes)
        conn.local(' '.join(cmd))


def my_sudo(connection, command):
    """
    A function that returns a sudo command and watcher for
    use with `connection.run()` under a pyinvoke context manager.
    """
    prompt = connection.config.sudo.prompt
    password = connection.config.sudo.password
    user = connection.config.sudo.user
    user_flags = ""
    if user is not None:
        user_flags = "-H -u {} ".format(user)
    cmd_str = "sudo -S -p '{}' {}{}".format(prompt, user_flags, command)
    watcher = FailingResponder(
        pattern=re.escape(prompt),
        response="{}\n".format(password),
        sentinel="Sorry, try again.\n",
    )
    return cmd_str, watcher


def deploy():
    global conn
    newdir = 'plant_insect_ai-%s' % _now()
    conn.run('rm -f %s' % _REMOTE_TMP_TAR)
    conn.put('dist/%s' % _TAR_FILE, _REMOTE_TMP_TAR)
    with conn.cd(_REMOTE_BASE_DIR):
        conn.sudo('mkdir %s' % newdir)
        # command, watcher = my_sudo(conn, "ls -al /var/log/nginx")
        # conn.run(command, watchers=[watcher])
        # conn.run("sudo ls -al")
        with conn.cd('%s/%s' % (_REMOTE_BASE_DIR, newdir)):
            conn.sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
        with conn.cd(_REMOTE_BASE_DIR):
            conn.sudo('rm -f quarrying_ai')
            conn.sudo('ln -s %s quarrying_ai' % newdir)
            conn.sudo('chown www-data:www-data quarrying_ai')
            conn.sudo('chown -R www-data:www-data %s' % newdir)
        with conn.settings(warn_only=True):
            conn.sudo('supervisorctl stop quarrying_ai')
            conn.sudo('supervisorctl start quarrying_ai')
            conn.sudo('/etc/init.d/nginx reload')


RE_FILES = re.compile('\r?\n')


def rollback():
    '''
    rollback to previous version
    '''
    global conn
    with conn.cd(_REMOTE_BASE_DIR):
        r = conn.run('ls -p -1')
        files = [s[:-1]
                 for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]
        files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
        r = conn.run('ls -l plant_insect_ai')
        ss = r.split(' -> ')
        if len(ss) != 2:
            print('ERROR: \'plant_insect_ai\' is not a symbol link.')
            return
        current = ss[1]
        print('Found current symbol link points to: %s\n' % current)
        try:
            index = files.index(current)
        except ValueError as e:
            print('ERROR: symbol link is invalid.')
            return
        if len(files) == index + 1:
            print('ERROR: already the oldest version.')
        old = files[index + 1]
        print('==================================================')
        for f in files:
            if f == current:
                print('      Current ---> %s' % current)
            elif f == old:
                print('  Rollback to ---> %s' % old)
            else:
                print('                   %s' % f)
        print('==================================================')
        print('')
        yn = conn.raw_input('continue? y/N ')
        if yn != 'y' and yn != 'Y':
            print('Rollback cancelled.')
            return
        print('Start rollback...')
        conn.sudo('rm -f plant_insect_ai')
        conn.sudo('ln -s %s plant_insect_ai' % old)
        conn.sudo('chown www-data:www-data plant_insect_ai')
        with conn.settings(warn_only=True):
            conn.sudo('supervisorctl stop plant_insect_ai')
            conn.sudo('supervisorctl start plant_insect_ai')
            conn.sudo('/etc/init.d/nginx reload')
        print('ROLLBACKED OK.')


def restore2local():
    '''
    Restore db to local
    '''
    global conn
    backup_dir = os.path.join(_current_path(), 'backup')
    fs = os.listdir(backup_dir)
    files = [f for f in fs if f.startswith(
        'backup-') and f.endswith('.sql.tar.gz')]
    files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
    if len(files) == 0:
        print('No backup files found.')
        return
    print('Found %s backup files:' % len(files))
    print('==================================================')
    n = 0
    for f in files:
        print('%s: %s' % (n, f))
        n = n + 1
    print('==================================================')
    print('')
    try:
        num = int(conn.raw_input('Restore file: '))
    except ValueError:
        print('Invalid file number.')
        return
    restore_file = files[num]
    yn = conn.raw_input('Restore file %s: %s? y/N ' % (num, restore_file))
    if yn != 'y' and yn != 'Y':
        print('Restore cancelled.')
        return
    print('Start restore to local database...')
    p = conn.raw_input('Input mysql root password: ')
    sqls = [
        f'drop database if exists {db_name};',
        f'create database {db_name};',
        'grant select, insert, update, delete on %s.* to \'%s\'@\'localhost\' identified by \'%s\';' % (
            db_name, db_user, db_password)
    ]
    for sql in sqls:
        conn.local(r'mysql -uroot -p%s -e "%s"' % (p, sql))
    with conn.lcd(backup_dir):
        conn.local('tar zxvf %s' % restore_file)
    conn.local(r'mysql -uroot -p%s plant_insect_ai < backup/%s' %
               (p, restore_file[:-7]))
    with conn.lcd(backup_dir):
        conn. local('rm -f %s' % restore_file[:-7])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        prog='fab',  # 程序名
        description='版本发布',  # 描述
        epilog='Copyright(r), 2023'  # 说明信息
    )
    # 定义位置参数:
    parser.add_argument('func')
    connect_kwargs = {'password': password}
    conn = Connection(host=host, port=port, user=user,
                      connect_kwargs=connect_kwargs)
    args = parser.parse_args()
    if args.func == 'build':
        build()
    elif args.func == 'deploy':
        deploy()
    elif args.func == 'rollback':
        rollback()
    elif args.func == 'restore2local':
        restore2local()
    else:
        print('未找到可执行指令')
    conn.close()
