#!/usr/bin/env python3
# coding:utf-8

'简单的消息队列'

__author__ = 'yang yang'

import asyncio
import time
import importlib
import logging
from contextlib import suppress

from components import orm
logging.basicConfig(level=logging.INFO)


async def task_add(queue, task_name, task_params):
    # 获取队列
    # queue = request.app['queue']
    # 从请求参数中获取任务名和参数
    # 动态引入任务模块
    task_module = importlib.import_module(f"queue_job.{task_name}")
    # 获取任务类并创建任务对象
    job_name = f"{task_name.capitalize()}Job"
    TaskClass = getattr(task_module, f"{job_name}")
    task = TaskClass(task_params)
    # 将任务加入队列
    # queue.put(dict(task_module = f"queue_job.{task_name}", job_name = job_name, task_params = task_params))
    await queue.put(task)


async def queue_worker(queue, db_config):
    # queue = app['queue']
    try:
        loop = asyncio.get_event_loop()
        # pool = loop.run_until_complete(create_db_pool(loop, db_config))
        pool = await create_db_pool(loop, db_config)
        # 设置定时器，每隔一定时间检测数据库连接
        check_db_conn_task = loop.create_task(check_db_connection(pool))
        while True:
            try:
                task = await queue.get()
                # if data is None or 'task_module' not in data or 'job_name' not in data:
                #     continue
                # task_module = importlib.import_module(data['task_module'])
                # TaskClass = getattr(task_module, data['job_name'])
                # task_params = None if 'task_params' not in data else data['task_params']
                # task = TaskClass(task_params)
                if task is None:
                    # print('task none')
                    # queue.task_done()
                    break
                print('starting execute query task...')
                # task.set_db_proxy(db)
                await task.async_execute()
                # if getattr(task, 'execute') and task.execute(loop):
                #     # print(task_module,job_name,task_params)
                #     task = None
                queue.task_done()
            except Exception as e:
                logging.error(msg="execute queue task error:" + str(e))
                # 退出进程前清理shared_db
    except asyncio.CancelledError:
        print("Queue worker task cancelled")
        pool.close()
        await pool.wait_closed()
        # if not check_db_conn_task.done():
        #     print('check_db_conn_task cancel')
        #     check_db_conn_task.cancel()
        # with suppress(asyncio.CancelledError):
        #     await check_db_conn_task
    # 执行coroutine
    # print('释放db pool')
    # await close_db_pool(pool)
    # loop.run_until_complete(close_db_pool(pool))
    # loop.stop()
    # loop.close()


async def check_db_connection(pool):
    while True:
        try:
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    await cur.fetchone()
            print("Database connection is alive.")
        except Exception as e:
            print("Database connection error:", e)

        await asyncio.sleep(60)


async def create_db_pool(loop, db_config):
    _db = orm.Model.init_db_proxy(loop=loop)
    await _db.make_pool(**db_config)

    return _db.pool


async def close_db_pool(pool):
    # 退出进程前清理shared_db
    pool.close()
    await pool.wait_closed()
