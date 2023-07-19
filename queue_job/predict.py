#!/usr/bin/env python3
# coding:utf-8

'简单的消息队列'

__author__ = 'yang yang'


import asyncio

from biz_model_predict import ai_predict


class PredictJob:
    def __init__(self, task):
        self.task = task

    def execute(self, loop):
        # 执行任务逻辑
        print(f"Executing task {self.task['task_uuid']}")
        # # 获取EventLoop:
        # loop = asyncio.get_event_loop()
        # # 执行coroutine
        loop.run_until_complete(self.async_execute())
        # loop.close()
        # loop = None

    async def async_execute(self):
        # print('before async_execute')
        if self.task is None:
            return
        self.task.status = 1
        await self.task.update()
        # await asyncio.sleep(10)
        # print('after sleep:', self.task)
        try:
            await ai_predict(self.task)
        except Exception as e:
            import traceback
            # 获取调用栈信息
            traceback_str = traceback.format_exc()
            # 打印或处理调用栈信息
            print('after async_execute error:\t\t\n\n', traceback_str)
