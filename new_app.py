#!/usr/bin/env python3
# coding:utf-8

# 我们的Web App建立在asyncio的基础上，因此用aiohttp写一个基本的

import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

# https://www.jb51.net/article/211203.htm
class MicroAPI(object):
    def __init__(self, loop) -> None:
        app = web.Application(loop=loop)
        self.app = app
        self.loop = loop
        self.registerRoutes()
    def registerRoutes(self) -> None:
        self.app.router.add_route('GET', '/', MicroAPI.index_request)
        self.app.router.add_get('/index', MicroAPI.index_request)
    async def run(self):
        srv = await self.loop.create_server(self.app.make_handler(), '0.0.0.0', 8488)
        logging.info(f'server started at http://127.0.0.1:8488...')
        return srv
    def index_request(request):
        return web.Response(body=r'<h1>欢迎访问病虫害识别API</h1>', content_type='text/html', charset='utf-8')
    
def main():
    # 返回asyncio事件循环
    loop = asyncio.get_event_loop()
    #运行事件循环，直到Future完成。
    loop.run_until_complete(MicroAPI(loop).run())
    # 运行和停止事件循环
    loop.run_forever()

if __name__ == '__main__':
    main()

