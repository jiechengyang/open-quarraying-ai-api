# !/usr/bin/env python3

# -*- coding=utf-8 -*-

__author__ = 'yangyang'

'中间件'

import json
import logging
from biz_helper import check_app_key_availability, cookie2user, COOKIE_NAME, error_json_response, get_request_client_real_ip, is_proxy_request
from aiohttp import web
from components.ak_sk_signture import SignatureAuth, SignatureAuthException

from components.apis import BIZ_CODE_AK_SK_AUTH_FAILED, BIZ_CODE_APP_NOT_EXIST, BIZ_CODE_OK


logging.basicConfig(level=logging.INFO)

'''
请求日志中间件
'''


async def logger_middleware(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        return (await handler(request))
    return logger

'''
session-cookie 会话认证中间件
'''


async def auth_middleware(app, handler):
    async def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/admin/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/login')
        return (await handler(request))
    return auth

'''
请求数据包解析中间件
'''


async def data_parse_middleware(app: web.Application, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data

'''
跨域访问中间件
'''


async def cors_middleware(app: web.Application, handler):
    async def middleware(request):
        if not is_proxy_request(request) and request.method == 'OPTIONS':
            # 设置 CORS 响应头
            response = web.Response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,X-Requested-With,X-Ca-Key,X-Ca-Timestamp,X-Ca-None,X-Ca-Signature-Headers,X-Ca-Signature'
            return response

        # 继续处理其他请求
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    return middleware

'''
统一响应中间件
'''


async def response_middleware(app: web.Application, handler):
    async def response(request):
        # logging.info('Response handler...')
        request_headers = dict(request.headers)
        is_ajax = 'X-Requested-With' in request_headers and request_headers['X-Requested-With'] == 'XMLHttpRequest'
        if request.path == '/favicon.ico':
            with open(r"./public/static/favicon.ico", "rb") as f:
                image_data = f.read()
            headers = {"Content-Type": "image/x-icon"}
            return web.Response(body=image_data, headers=headers)
        try:
            r = await handler(request)
        except BaseException as e:
            if is_ajax:
                resp = web.json_response(
                    data=dict(code=101, message=str(e), data=None))
                return resp
            resp = web.Response(body='服务器内部错误'.encode('utf-8'))
            resp.content_type = 'text/plain;charset=utf-8'
            return resp
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(
                    r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                r['__user__'] = None
                # r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(
                    template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        # if isinstance(r, int) and t >= 100 and t < 600:
        #     return web.Response(t)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        if is_ajax:
            resp = web.json_response(
                data=dict(code=101, message=str(r), data=None))
            return resp
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


'''
签名验证中间件
'''


@web.middleware
async def signture_check_middleware(request: web.Request, handler):
    if request.path == '/' or request.path.find('/static/') >= 0 or request.path.find('/uploads/') >= 0:
        return await handler(request)
    headers = dict(request.headers)
    headers = {key.lower(): value for key, value in headers.items()}
    # print('request_headers:', headers, request.url)
    if 'x-ca-key' not in headers:
        return error_json_response('无权访问，应用授权key未提供', BIZ_CODE_APP_NOT_EXIST)
    check_code, err_msg, app_client = await check_app_key_availability(headers['x-ca-key'])
    if check_code != BIZ_CODE_OK:
        return error_json_response(err_msg, check_code)
    sign_auth = SignatureAuth(app_client.app_key, app_client.app_secret)
    request_real_ip = get_request_client_real_ip(request)
    sign_auth.setIsNginxProxy(is_proxy_request(request))
    sign_auth.setRequstIp(request_real_ip)
    body = None
    if request.method == 'post':
        body = request.post()

    try:
        is_validated_sign = sign_auth.verify_signature(
            request.method, request.url, headers, body)
        if is_validated_sign:
            return await handler(request)
        return error_json_response('无权访问，签名错误', BIZ_CODE_AK_SK_AUTH_FAILED)
    except SignatureAuthException as e:
        return error_json_response(e.message, BIZ_CODE_AK_SK_AUTH_FAILED)
