#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Default configurations.
'''

__author__ = 'Yang Yang'

configs = {
    'debug': True,
    'host': '127.0.0.1',  # 0.0.0.0
    'local_ips': ['127.0.0.1', '172.16.0.0/12', '192.168.*.*'],
    'port': 4646,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'db': 'quarrying_ai'
    },
    'session': {
        'secret': 'quarrying'
    },
    'img_url': 'http://127.0.0.1:4646/uploads/'
}
