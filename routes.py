#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

' url route handlers '

import asyncio
import os
import biz_dict
from biz_model_predict import ai_predict
from components.message_queue import task_add
from components.models import App
from components.apis import BIZ_CODE_APP_FUNC_LIMITED
from biz_helper import MAX_UPLOAD_TASK_IMAGE_SIZE, UPLOAD_PATH, add_biz_error_log, add_biz_info_log, create_ai_task, filter_dict, get_app_by_key, get_current_date, get_currnet_timestamp, get_file_ext, get_page_index, get_request_client_real_ip, get_task_by_uuid, get_tasks, is_image_url, is_proxy_request, success_json_response, error_json_response, BIZ_CODE_NOT_FOUND, timestamp_format, timestamp_to_datetime
from aiohttp import web
from coroweb import get, post
from config.bapp import configs

# sys.path.insert(0, os.path.join(os.getcwd(), 'components'))
from components.apis import Page, APIValueError, APIResourceNotFoundError, APIPermissionError


# -------------------- routes -------------------- #
@get('/')
def index(*, page='1'):
    page_index = get_page_index(page)
    # num = yield from Blog.findNumber('count(id)')
    page = Page(page_index=page_index, page_size=20, item_count=100)
    print('page:', page)
    return {
        '__template__': 'index.html',
        'title': '病虫害识别',
        'page_index': page_index,
        'page': page,
        'blogs': []
    }


@get('/ai/my/app')
async def api_get_app(request: web.Request):
    app = await App.findByAppKey(request.headers.get('X-Ca-Key'))
    app['status_text'] = '禁用' if app.status == 0 else '启用'
    app.expired_at = 0 if app.expired_at == 0 else timestamp_format(
        app.expired_at)
    app['expired_at_text'] = '永不过期' if app.expired_at == 0 else timestamp_to_datetime(
        app.expired_at)
    app.created_at = timestamp_format(app.created_at)
    if app.funcs == '*':
        app['funcs_text'] = '全部'
    else:
        type_dicts = biz_dict.ai_task_type_dict
        funcs_list = app.funcs.split('|')
        funcs_text_list = []
        for i in range(len(type_dicts)):
            type_dict = type_dicts[i]
            if type_dict['key'] in funcs_list:
                funcs_text_list.append(type_dict['value'])
        app['funcs_text'] = '|'.join(funcs_text_list)

    app = filter_dict(app, 'updated_at')

    return success_json_response(app)


@post('/ai/tasks')
async def api_task_list(request: web.Request):
    try:
        if request.headers.get('Content-Type').find('application/json') >= 0:
            data = await request.json()
        else:
            data = await request.post()

        tasks = await get_tasks(data)

        return success_json_response(tasks)
    except Exception as e:
        import traceback
        # 获取调用栈信息
        traceback_str = traceback.format_exc()
        # 打印或处理调用栈信息
        print('after api_task_list error:\t\t\n\n', traceback_str)

        return error_json_response(str(e))


@post('/ai/task/{id}/result')
async def api_task_view(id, request: web.Request):
    try:
        task = await get_task_by_uuid(id)
        if is_proxy_request(request):
            img_url_fix = configs.img_url.replace('http', request.scheme)
        else:
            img_url_fix = f"{request.scheme}://{request.host}/uploads/"
        if task['result_img_url']:
            task['result_img_url'] = f"{img_url_fix}{task['result_img_url']}"
        task.created_at = timestamp_format(task.created_at)
        task = filter_dict(task, 'id', 'app_key', 'img_local_path', 'result_img_path',
                           'img_url', 'req_params', 'req_ip', 'req_user_agent', 'remark', 'updated_at')
        return success_json_response(data=task, message=task['status_text'])
    except Exception as e:
        import traceback
        # 获取调用栈信息
        traceback_str = traceback.format_exc()
        # 打印或处理调用栈信息
        print('after api_task_view error:\t\t\n\n', traceback_str)

        return error_json_response(str(e))


'''
 * 被称为 "命名位置参数分隔符"。
 它的作用是指示在它之前的参数为普通的位置参数，而在它之后的参数必须以关键字参数的形式进行传递。
'''


@post('/ai/task/create')
async def api_create_task(request: web.Request):
    app_client = await get_app_by_key(request.headers.get('X-Ca-Key'))
    data = {}
    if request.headers.get('Content-Type').find('application/json') >= 0:
        data = await request.json()
        func_code = '' if 'func_code' not in data else data['func_code']
        validate_create_task_func_code(func_code, app_client.funcs)
        if 'img_url' not in data or not data['img_url'].strip():
            raise APIValueError('img_url', '创建失败，识别图片网络地址不能为空')
        check_result = is_image_url(data['img_url'])
        if not check_result:
            raise APIValueError('img_url', '创建失败，识别图片网络地址格式错误：非图片')
        if isinstance(check_result, int):
            file_size = check_result
            max_size = max_size = get_predict_max_upload_img_size_by_func_code(
                func_code)
            if file_size > max_size:
                raise APIValueError(
                    'image_size', f'创建失败，图片超过最大文件限制({MAX_UPLOAD_TASK_IMAGE_SIZE / 1024 / 1024}M)')

        user_id = None if 'user_id' not in data else data['user_id']
        if user_id == None:
            raise APIValueError('user_id', f'创建失败，操作人ID缺失')
        req_params = '' if 'req_params' not in data else data['req_params']
        remark = '' if 'req_params' not in data else data['remark']
        data = dict(func_code=func_code, img_url=data['img_url'],
                    req_params=req_params, remark=remark, img_local_path='')
    else:
        func_code = None
        req_params = ''
        remark = ''
        user_id = None
        relative_path = None
        file_size = 0
        async for field in (await request.multipart()):
            if field.name == 'func_code':
                func_code = await field.text()
            elif field.name == 'req_params':
                req_params = await field.text()
            elif field.name == 'remark':
                remark = await field.text()
            elif field.name == 'user_id':
                user_id = await field.text()
            elif field.name == 'image':
                ext = get_file_ext(field.filename)
                if ext not in ['jpg', 'jpeg', 'png', 'bmp']:
                    raise APIValueError(
                        'image_type', '创建失败，识别图片格式错误，仅支持jpg,png,bmp')
                # content = await field.read()
                # file_size = len(content)
                # You cannot rely on Content-Length if transfer is chunked.
                path, sub_path = make_task_image_upload_path(func_code)
                # 统一处理为jpg
                new_filename = f'{str(get_currnet_timestamp())}.jpg'
                filepath = os.path.join(path, new_filename)
                relative_path = f'uploads/{sub_path}/{new_filename}'
                with open(filepath, 'wb') as f:
                    while True:
                        # 8192 bytes by default.
                        chunk = await field.read_chunk()
                        if not chunk:
                            break
                        file_size += len(chunk)
                        f.write(chunk)

        validate_create_task_func_code(func_code, app_client.funcs)
        if user_id is None or user_id == 0 or user_id == '0':
            raise APIValueError('user_id', f'创建失败，操作人ID缺失')
        if relative_path is None:
            raise APIValueError(
                'image', f'创建失败，未上传图片')
        max_size = get_predict_max_upload_img_size_by_func_code(
            func_code)
        if file_size > max_size:
            os.remove(filepath)
            raise APIValueError(
                'image_size', f'创建失败，图片超过最大文件限制({max_size / 1024 / 1024}M)')
    data = dict(func_code=func_code, img_local_path=relative_path,
                req_params=req_params, remark=remark, img_url='')
    data['task_type'] = func_code
    data['app_key'] = app_client.app_key
    data['req_ip'] = get_request_client_real_ip(request)
    data['req_user_agent'] = request.headers.get('User-Agent', '')
    try:
        task = await create_ai_task(data)
        await add_biz_info_log(module='task', action='create_task',
                               message='成功创建ai识别任务', data=task, user_id=1, ip=data['req_ip'])
        # await ai_predict(task)
        task['user_id'] = user_id
        await task_add(request.app['queue'], 'predict', task)
        task.created_at = timestamp_format(task.created_at)
        task = filter_dict(task, 'updated_at', 'req_ip',
                           'req_user_agent', 'img_local_path', 'img_url', 'id')
        return success_json_response(data=task)
    except Exception as e:
        msg = str(e)
        await add_biz_error_log(module='task', action='create_task',
                                message='失败创建ai识别任务:' + msg, data=data, user_id=1, ip=data['req_ip'])
        return error_json_response(message=msg)


# -------------------- routes -------------------- #

def get_predict_max_upload_img_size_by_func_code(func_code):
    max_size = MAX_UPLOAD_TASK_IMAGE_SIZE
    if func_code.endswith('_disease'):
        max_size = 4 * 1024 * 1024
    return max_size


'''
验证识别功能码
'''


def validate_create_task_func_code(func_code, funcs: str):
    if func_code is None:
        raise APIValueError('func_code', '创建失败，识别功能码必须提供')
    if not func_code.strip():
        raise APIValueError('func_code', '创建失败，识别功能码不能为空')
    task_type_dict = biz_dict.findDictByKey(
        biz_dict.ai_task_type_dict, func_code)
    if not task_type_dict:
        raise APIValueError('func_code', '创建失败，非法的识别功能码')
    func_list = funcs.split('|')
    if funcs != '*' and func_code not in func_list:
        raise APIPermissionError('创建失败，没有获得此识别功能', BIZ_CODE_APP_FUNC_LIMITED)
    # 判断当前的应用授权是否支持该项识别


'''
生成返回识别任务功能的上传临时目录
'''


def make_task_image_upload_path(func_code):
    sub_dir = f'task/{func_code}/{get_current_date()}'
    dir = f'{UPLOAD_PATH}/{sub_dir}'
    not os.path.isdir(dir) and os.makedirs(dir, mode=0o755, exist_ok=True)

    return dir, sub_dir
