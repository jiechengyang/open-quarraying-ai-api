#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'yang yang'

'''
业务助手
'''
import os
import re
import time
import json
import logging
import hashlib
from typing import Dict
from urllib.parse import urlparse
import biz_dict
from biz_exceptions import TaskBizException
from datetime import datetime, timedelta
from aiohttp import web
from config.bapp import configs
from components.models import DiseaseLibary, Log, User, App, Task, TaskResult, next_id
from components.apis import BIZ_CODE_OK, BIZ_CODE_APP_DISABLED, BIZ_CODE_APP_EXPIRED, BIZ_CODE_APP_NOT_EXIST, BIZ_CODE_TASK_NOT_FOUND, BIZ_CODE_TASK_REACHED_DAY_LIMIT, BIZ_CODE_VALUE_ERROR,BIZ_CODE_NOT_FOUND
import requests
import socket
import ipaddress

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
PUBLIC_PATH = os.path.join(ROOT_PATH, 'public')
UPLOAD_PATH = os.path.join(ROOT_PATH, 'public/uploads')
STATIC_PATH = os.path.join(ROOT_PATH, 'public/static')
MAX_UPLOAD_TASK_IMAGE_SIZE = 15 * 1024 * 1024
# -------------------- biz tool code -------------------- #

'''
判断request是否为反向代理发起
'''
def is_proxy_request(request):
    headers = dict(request.headers)
    return 'x-forwarded-for' in request.headers or 'x-real-ip' in headers

'''
判断是否是内网地址
'''



def is_internal_ip(ip, private_networks = []):
    def parse_wildcard_to_network(ip_wildcard):
        # 将通配符 IP 转换为 IP 网段
        ip_parts = ip_wildcard.split('.')
        network_mask = '.'.join(ip_parts[:2]) + '.0.0'
        return ipaddress.ip_network(network_mask)
    # 添加内部 IP 地址范围，支持通配符配置
    private_networks = configs.local_ips + private_networks
    for private_ip in private_networks:
        if '*' in private_ip:
            # 处理通配符 IP
            private_network = parse_wildcard_to_network(private_ip)
        else:
            # 处理普通 IP 网段
            private_network = ipaddress.ip_network(private_ip)

        if ipaddress.ip_address(ip) in private_network:
            return True

    host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
    # 检查是否是本机 IP
    if ip in host_ips:
        return True

    return False

'''
判断一个URL地址是否有效
'''


def is_valid_url(url):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme and parsed_url.netloc)


'''
字典列表排序
'''


def sort_dict_list(dicts, key, reverse=False):
    # dicts.sort(key=lambda item: item.get(key))

    return sorted(dicts, key=lambda item: item.get(key), reverse=reverse)


'''
将小数转成百分比
'''


def bfb(value, round_val=True):
    percentage = value * 100
    if round_val:
        percentage = round(percentage, 3)
    percentage = f"{percentage: .2f}"
    formatted_percentage = f"{percentage}%"

    return percentage, formatted_percentage


'''
获取文件名后缀
'''


def get_file_ext(file_path):
    ext = file_path.split(".")[-1]
    return str(ext).lower()


'''
获取文件的hash值
'''


def calculate_file_hash(file_path, algorithm='md5'):
    hash_object = hashlib.new(algorithm)

    with open(file_path, 'rb') as file:
        # 逐块读取文件内容并更新哈希对象
        for chunk in iter(lambda: file.read(4096), b''):
            hash_object.update(chunk)

    # 获取最终的哈希值
    file_hash = hash_object.hexdigest()
    return file_hash

# 自定义 JSON 序列化函数


def custom_json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


def success_json_response(data, message='ok'):
    return web.json_response(dict(code=0, data=data, message=message), dumps=custom_json_dumps)


def error_json_response(message, code=-1, data=None):
    return web.json_response(dict(code=code, data=data, message=message))


def timestamp_format(float_time):
    return int(float_time)


def get_currnet_timestamp():
    return timestamp_format(time.time())


def timestamp_to_datetime(timestamp, format='%Y-%m-%d %H:%M:%S'):
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime(format)


def get_current_date():
    return get_current_datetime("%Y-%m-%d")


def get_current_datetime(format='%Y-%m-%d %H:%M:%S'):
    now = datetime.now()
    return now.strftime(format)


def datetime_to_timestamp(datetime: str, is_int=False):
    # 判断是否为日期+时间格式
    if re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}$', datetime):
        date_format = '%Y-%m-%d %H:%M:%S'
    # 判断是否为日期格式
    elif re.match(r'^\d{4}-\d{2}-\d{2}$', datetime):
        date_format = '%Y-%m-%d'
    else:
        raise ValueError('Invalid date string')

    t = time.strptime(datetime, date_format)
    tm = time.mktime(t)
    return tm if not is_int else int(tm)


'''
获取当天的开始与结束时间戳
'''


def get_today_st_et_timestamp():
    # 获取当前时间
    now = datetime.now()
    # 获取今天的开始时间
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_timestamp = int(start_of_day.timestamp())
    # 获取今天的结束时间
    end_of_day = start_of_day + timedelta(days=1, microseconds=-1)
    end_timestamp = int(end_of_day.timestamp())
    return start_timestamp, end_timestamp


def get_request_client_real_ip(request: web.Request):

    return request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote


def is_image_url(url):
    try:
        response = requests.head(url)
        content_type = response.headers.get('content-type')
        if content_type and content_type.startswith('image'):
            content_length = response.headers.get('Content-Length')
            if content_length:
                file_size = int(content_length)
                return file_size

            return True
    except requests.exceptions.RequestException:
        pass

    return False


'''
根据指定的属性列表来过滤字典中的属性
usage: filter_dict(dicts, 'field1', 'field2')
'''


def filter_dict(dictionary, *keys):
    return {key: value for key, value in dictionary.items() if key not in keys}


COOKIE_NAME = 'plant_insect_ai_session'
_COOKIE_KEY = configs.session.secret


def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p


def user2cookie(user, max_age):
    '''
    Generate cookie str by user.
    '''
    # build cookie string by: id-expires-sha1
    expires = str(int(time.time() + max_age))
    s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)


def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<',
                '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


async def cookie2user(cookie_str):
    '''
    Parse cookie and load user if cookie is valid.
    '''
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if int(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None
# -------------------- biz tool code -------------------- #

# -------------------- biz code -------------------- #


async def get_tasks(conditions: dict = None):
    where = '1'
    args = []
    if 'keyword' in conditions and str(conditions['keyword']).strip():
        where += ' AND (task_name LIKE %s)'
        args.append(f"%{conditions['keyword']}%")
    if 'task_type' in conditions and str(conditions['task_type']).strip():
        where += ' AND (task_type = ?)'
        args.append(conditions['task_type'])
    if 'status' in conditions and str(conditions['status']).isdigit():
        where += ' AND (status = ?)'
        args.append(conditions['status'])
    if 'start_time' in conditions and str(conditions['start_time']).strip():
        where += ' AND (created_at >= ?)'
        args.append(datetime_to_timestamp(conditions['start_time']))
    if 'end_time' in conditions and str(conditions['end_time']).strip():
        where += ' AND (created_at <= ?)'
        args.append(datetime_to_timestamp(conditions['end_time']))
    if len(args) == 0:
        args = None
    if 'page_size' in conditions and str(conditions['page_size']).isdigit():
        page_size = int(conditions['page_size'])
    else:
        page_size = 10

    if 'page' in conditions and str(conditions['page']).isdigit():
        page = int(conditions['page'])
        page_index = (page - 1) * page_size
    else:
        page = 1
        page_index = 0
    tasks = await Task.findAll(where=where, args=args, limit=(page_index, page_size), columns=['id', 'task_uuid', 'task_type', 'task_name', 'img_url', 'req_ip', 'req_user_agent', 'status', 'finshed_at', 'created_at'])
    for i in range(len(tasks)):
        tasks[i] = __task_format(tasks[i])
    return tasks


async def get_task_by_uuid(uuid):
    task = await Task.findByUUID(uuid)
    if task is None:
        raise TaskBizException(
            message="访问失败，任务不存在，请检查任务ID", code=BIZ_CODE_TASK_NOT_FOUND)
    lasted_task_result = await TaskResult.findByTaskUUID(task.task_uuid)
    if lasted_task_result and lasted_task_result.class_code:
        disease = await DiseaseLibary.findByCode(lasted_task_result.class_code)
        if disease is not None:
            if isinstance(disease.prevent_ways, str):
                lasted_task_result['prevent_ways'] = json.loads(
                    disease.prevent_ways)
            else:
                lasted_task_result['prevent_ways'] = disease.prevent_ways
    return __task_format(task, lasted_task_result)


def __task_format(task, lasted_task_result=None):
    task_type_dict = biz_dict.findTaskTypeDict(task.task_type)
    task['task_type_text'] = ''
    if task_type_dict is not None:
        task['task_type_text'] = task_type_dict['value']
    task['status_text'] = biz_dict.findTaskStatusDict(task.status)
    task['result_img_url'] = ''
    if lasted_task_result is not None and 'result_img_path' in lasted_task_result and lasted_task_result['result_img_path']:
        task['result_img_url'] = lasted_task_result['result_img_path']
        lasted_task_result.pop('result_img_path')
    if lasted_task_result is not None and lasted_task_result.result:
        task['task_result'] = filter_dict(
            json.loads(lasted_task_result.result), 'save_img_path')
    else:
        task['task_result'] = None
    # print('task.status:', task, lasted_task_result)
    if lasted_task_result is not None and 'prevent_ways' in lasted_task_result:
        task['prevent_ways'] = lasted_task_result['prevent_ways']
    else:
        task['prevent_ways'] = None
    task.finshed_at = 0 if not task.finshed_at else timestamp_format(
        task.finshed_at)
    return task


'''
获取 应用授权信息
'''


async def get_app_by_key(app_key) -> App:
    return await App.findByAppKey(app_key)

'''
校验应用客户端是否可用
'''


async def check_app_key_availability(app_key):
    app_client = await get_app_by_key(app_key)
    if not app_client:
        return BIZ_CODE_APP_NOT_EXIST, '无权访问，非法应用授权key', None
    if app_client.status == 0:
        return BIZ_CODE_APP_DISABLED, '无权访问，该应用已停用', None
    if app_client.expired_at > 0 and app_client.expired_at < time.time:
        return BIZ_CODE_APP_EXPIRED, '无权访问，该应用授权已过期', None

    return BIZ_CODE_OK, '', app_client

'''
校验应用授权ai识别是否达到当日上限
'''


async def validate_task_func_daily_request_limit(app_key, func_code):
    st, et = get_today_st_et_timestamp()
    count = await Task.count('id', "app_key=? AND task_type=? AND (created_at >= ? AND created_at <= ?)", [app_key, func_code, st, et])
    max_num = biz_dict.findTaskDayMaxRequestNum(func_code)
    if count == max_num:
        return True
    return False

'''
创建识别任务
'''


async def create_ai_task(fields: Dict):
    if 'task_type' not in fields:
        raise KeyError('task_type must be exist')
    if 'app_key' not in fields:
        raise KeyError('app_key must be exist')
    task_type = fields['task_type']
    task_type_dict = biz_dict.findTaskTypeDict(task_type)
    task_type_text = task_type_dict['value']
    if await validate_task_func_daily_request_limit(fields['app_key'], task_type):
        raise TaskBizException(
            message=f'创建失败，{task_type_text}次数已经达到当日上限', code=BIZ_CODE_TASK_REACHED_DAY_LIMIT)
    task_uuid = next_id()
    datetime = get_current_datetime()
    task_name = f'{task_type}_{datetime}_识别'
    fields['task_uuid'] = task_uuid
    fields['task_name'] = task_name
    fields['status'] = 0
    task = Task(**fields)
    res = await task.save()
    if res > 0:
        return task

    return None

'''
写入操作日志-级别为基础
'''


async def add_biz_info_log(module, action, message, data, user_id=0, ip='127.0.0.1'):
    return await __add_biz_log(level='info', module=module, action=action, message=message, data=json.dumps(data), user_id=user_id, ip=ip)

'''
写入操作日志-级别为警告
'''


async def add_biz_warning_log(module, action, message, data, user_id=0, ip='127.0.0.1'):
    return await __add_biz_log(level='warning', module=module, action=action, message=message, data=json.dumps(data), user_id=user_id, ip=ip)

'''
写入操作日志-级别为调试
'''


async def add_biz_debug_log(module, action, message, data, user_id=0, ip='127.0.0.1'):
    return await __add_biz_log(level='debug', module=module, action=action, message=message, data=json.dumps(data), user_id=user_id, ip=ip)

'''
写入操作日志-级别为错误
'''


async def add_biz_error_log(module, action, message, data, user_id=0, ip='127.0.0.1'):
    return await __add_biz_log(level='error', module=module, action=action, message=message, data=json.dumps(data), user_id=user_id, ip=ip)


async def __add_biz_log(level, module, action, message, data, user_id=0, ip='127.0.0.1'):
    log = Log(module=module, action=action, message=message,
              data=json.dumps(data, ensure_ascii=False), user_id=user_id, ip=ip, level=level)
    res = await log.save()

    return res
# -------------------- biz code -------------------- #
