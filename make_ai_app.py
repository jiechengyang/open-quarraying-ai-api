#!/usr/bin/env python3

# -*- coding:utf-8 -*-

'生成 ai 应用端'

__author__ = 'yang yang'

import asyncio
import secrets
import string
from datetime import datetime, timedelta
from components.orm import Model
from components.models import App, next_id
from config.bapp import configs


def generate_random_string(length=16):
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def get_timestamp_after_days(n):
    current_time = datetime.now()
    delta = timedelta(days=n)
    new_time = current_time + delta
    # timestamp = int(new_time.timestamp())
    return new_time.timestamp()


async def make_app(loop, app_name, expired_at, result_hock=''):
    db = Model.init_db_proxy(loop)
    await db.make_pool(**configs.db)
    while True:
        app_key = generate_random_string(16)
        old_app = await App.findByAppKey(app_key=app_key)
        if not old_app:
            break

    app = App(app_key=app_key,
              app_secret=generate_random_string(32),
              app_name=app_name,
              expired_at=expired_at,
              result_hock=result_hock,
              status=1
              )
    res = await app.save()
    if res > 0:
        print(
            f'应用[{app.app_name}]创建成功，请妥善保存：app_key = {app.app_key} app_secret = {app.app_secret}')
    else:
        print(f'应用创建失败')
    db.pool.close()
    await db.pool.wait_closed()
if __name__ == '__main__':
    while True:
        app_name = input('请输入ai 应用名(不能为空)：')
        if app_name.strip():
            break
    try:
        expired_at = int(input('请输入ai 应用过期天数(不输入或者输入0表示永不过期)：'))
    except ValueError:
        expired_at = 0
    if expired_at < 0:
        print('过期天数为负数')
        exit(0)
    expired_at = 0 if expired_at == 0 else get_timestamp_after_days(expired_at)
    result_hock = input('请输入识别结果hock地址（http://|https://开头)')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_app(loop, app_name, expired_at, result_hock))
    loop.close()
