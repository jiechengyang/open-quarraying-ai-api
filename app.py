#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from contextlib import suppress
import time
import os
import logging
import subprocess
import argparse
import asyncio
import psutil
from tabulate import tabulate
from contextlib import suppress
import signal
from components.default_middleware import cors_middleware, logger_middleware, response_middleware, signture_check_middleware
from components.message_queue import queue_worker
# from coroweb import add_routes, add_static, add_uploads
from coroweb import add_route, add_static, add_uploads
from components import orm
from config.bapp import configs
from jinja2 import Environment, FileSystemLoader
from aiohttp import web
from datetime import datetime
from routes import index,api_get_app,api_task_list,api_task_view,api_create_task

__author__ = 'yang yang'

current_sys_run_time = None
'''
async web application.
'''

'''
静态-路由初始化
'''
def init_routes(app):
    add_route(app, index)
    add_route(app, api_get_app)
    add_route(app, api_task_list)
    add_route(app, api_task_view)
    add_route(app, api_create_task)

'''
初始化模板引擎
'''


def init_jinja2(app, **kw):
    options = dict(
        autoescape=kw.get('autoescape', True),
        block_start_string=kw.get('block_start_string', '{%'),
        block_end_string=kw.get('block_end_string', '%}'),
        variable_start_string=kw.get('variable_start_string', '{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'public/templates')
    # logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


'''
时间格式化
'''


def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'%s秒' % delta
    if delta < 3600:
        return u'%s分钟' % (delta // 60)
    if delta < 86400:
        return u'%s小时' % (delta // 3600)
    return u'%s天' % (delta // 86400)


is_clear_context = False

'''
aio http server app 启动 事件回调
'''


async def startup(app: web.Application):
    global is_clear_context
    global current_sys_run_time
    current_sys_run_time = time.time()
    runtime_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runtime')
    if not os.path.isdir(runtime_path):
        os.mkdir(runtime_path)
    with open(f"{runtime_path}/app_runtime", 'w') as f:
        f.write(str(current_sys_run_time))
        f.close()
    loop = asyncio.get_running_loop()
    app['queue'] = asyncio.Queue()
    task = loop.create_task(queue_worker(app['queue'], configs.db))
    app['worker_task'] = task
    # 创建并启动数据库连接池
    _db = orm.Model.init_db_proxy(loop=loop)
    await _db.make_pool(**configs.db)
    app['_db'] = _db
    # queue = asyncio.Queue()
    # app['queue'] = queue
    is_clear_context = False

'''
aio http server app cleanup 事件回调
'''


async def cleanup(app: web.Application):
    await clearContext(app)

'''
aio http server app 退出 事件回调
'''


async def shutdown(app: web.Application):
    print('服务退出了.....')
    global current_sys_run_time
    current_sys_run_time = None
    run_time_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runtime/app_runtime')
    if os.path.isfile(run_time_file):
        os.unlink(run_time_file)
    if not is_clear_context:
        await clearContext(app)

'''
清除app上下文：数据库连接池、队列连接池等
'''


async def clearContext(app: web.Application):
    global is_clear_context
    if 'worker_task' in app:
        if not app['worker_task'].done():
            app['worker_task'].cancel()
        with suppress(asyncio.CancelledError):
            await app['worker_task']
    if '_db' in app:
        # 关闭数据库连接池
        app['_db'].pool.close()
        await app['_db'].pool.wait_closed()
    if 'queue' in app:
        queue = app['queue']
        # queue.put_nowait(None)
        # worker_task = app['worker_task']
        # await worker_task
        await queue.join()

    is_clear_context = True

'''
启动api服务
'''


def run_app():
    app = web.Application(middlewares=[
        cors_middleware,
        logger_middleware,
        # auth_factory,
        signture_check_middleware,
        response_middleware
    ])
    loop = asyncio.get_event_loop()
    # app.cleanup_ctx.append(create_message_queue)
    app.on_startup.append(startup)
    # app.on_cleanup.append(cleanup)
    app.on_shutdown.append(shutdown)

    # def on_shutdown(signame):
    #     print(f"Received exit signal {signame}. Starting graceful shutdown.")
    #     loop.create_task(shutdown())

    # 信号处理：默认情况下，supervisorctl stop 命令发送的是 SIGTERM 信号来终止进程。但是，有些进程可能无法正常处理该信号并停止运
    # for signame in {"SIGINT", "SIGTERM"}:
    #     loop.add_signal_handler(
    #         getattr(signal, signame), lambda: asyncio.ensure_future(on_shutdown(signame)))

    # 初始化模板引擎
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    # 动态-初始化路由(内存暂用会小于静态路由)
    # add_routes(app, 'routes')
    # 静态-初始化路由
    init_routes(app)
    # 初始化静态资源
    add_static(app)
    # 初始化上传资源
    add_uploads(app)
    logging.info(f'server started on http://{configs.host}:{configs.port} ...')
    try:
        web.run_app(app, host=configs.host, port=configs.port)
    except:
        loop.create_task(shutdown())


'''
获取指定端口的进程号
'''


def get_port_process_id(port):
    cmd = f'lsof -i:{port} -t'
    output = subprocess.check_output(cmd, shell=True)
    pid = int(output.decode().strip()) if output else None

    return pid


'''
关闭app服务，通过对应的端口号
'''


def stop_app(port):
    print("stop app")
    pid = get_port_process_id(port)
    if pid:
        print(f"Terminating process with PID: {pid}")
        os.kill(pid, signal.SIGTERM)


'''
获取指定端口对应进程信息
'''


def get_process_info(port):
    for proc in psutil.process_iter(['pid', 'memory_info', 'num_threads']):
        try:
            pinfo = proc.as_dict(attrs=['pid', 'memory_info', 'num_threads'])
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    return pinfo
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return None


'''
获取进程下所有线程的内存暂用
'''


def get_thread_memory_usage(pid):
    thread_info = []
    process = psutil.Process(pid)
    for thread in process.threads():
        thread_id = thread.id
        thread_memory_info = process.memory_info()
        thread_memory_usage = f'{bytes_to_megabytes(thread_memory_info.rss)} mb'
        thread_info.append((thread_id, thread_memory_usage))
    return thread_info


'''
获取服务当前运行状态（内存和线程数）
'''


def show_app_running_status(port):
    process_info = get_process_info(port)
    if process_info:
        pid = process_info['pid']
        memory_usage = process_info['memory_info'].rss
        thread_count = process_info['num_threads']
        thread_info = get_thread_memory_usage(pid)

        print(f"Process PID: {pid}")
        run_time_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runtime/app_runtime')
        if os.path.isfile(run_time_file):
            with open(run_time_file, 'r') as f:
                current_sys_run_time = f.readline()
                f.close()
            
            print(f"Process Already Running: {datetime_filter(float(current_sys_run_time))}")
        print(
            f"Memory Usage: {memory_usage} bytes ({bytes_to_megabytes(memory_usage)} mb)")
        print(f"Thread Count: {thread_count}")

        thread_table = tabulate(thread_info, headers=[
                                "Thread ID", "Memory Usage"], tablefmt="grid")
        print("Thread Memory Usage:")
        print(thread_table)
    else:
        print(f"No process found running on port {port}")


'''
重启服务
'''


def restart_app(port):
    stop_app(port)
    run_app()


'''
字节转mb
'''


def bytes_to_megabytes(bytes):
    megabytes = bytes / (1024 * 1024)
    return megabytes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='MiniApi',
        description='mini web引擎、控制终端',
        epilog='Copyright(r), 2023'
    )
    parser.add_argument(
        '-c', '--cmd', help='usage start restart stop status', default='start', required=False)
    args = parser.parse_args()
    cmd = str(args.cmd).lower()
    if cmd == 'start':
        run_app()
    elif cmd == 'stop':
        stop_app(configs.port)
    elif cmd == 'restart':
        restart_app(configs.port)
    elif cmd == 'status':
        show_app_running_status(configs.port)
    else:
        print('Invalid command...')
