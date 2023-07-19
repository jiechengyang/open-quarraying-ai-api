# !/usr/bin/env python3

# -*- coding:utf-8 -*-

__author__ = 'yang yang'

'应用客户端签名认证'


import base64
import hashlib
import hmac
import time

from biz_helper import is_internal_ip
'''
签名规则算法
'''


class SignatureAuthException(Exception):
    def __init__(self, message='', *args: object) -> None:
        super().__init__(*args)
        self.message = message


class SignatureAuth:
    def __init__(self, ak, sk, timeout=300):
        self.ak = ak
        self.sk = sk
        self.timeout = timeout

    def setRequstIp(self, ip):
        self.request_ip = ip

    def setIsNginxProxy(self, proxy):
        self.nginx_proxy = proxy

    def generate_signature(self, method, url, headers, body=None):
        content_md5 = self.calculate_content_md5(body)
        signature_headers = headers.get(
            'X-Ca-Signature-Headers', 'x-ca-key,x-ca-timestamp,x-ca-none').lower()
        signature_header_key_list = signature_headers.split(',')
        signature_header_val_list = [headers.get(
            key.lower()) for key in signature_header_key_list]
        sign_arr = [
            method.upper(),
            headers.get('Accept', '*/*'),
            content_md5,
            headers.get('Content-Type', ''),
            '\n'.join(signature_header_val_list),
            str(url)
        ]
        signing_str = self.build_signing_string(sign_arr)
        signature = self.calculate_signature(signing_str)
        return signature

    def calculate_content_md5(self, body):
        if body:
            md5 = hashlib.md5()
            md5.update(body.encode('utf-8'))
            content_md5 = base64.b64encode(md5.digest()).decode('utf-8')
            return content_md5
        return ''

    def build_signing_string(self, sign_arr):
        str = '\n'.join(sign_arr)
        return str

    def calculate_signature(self, signing_str):
        signature = hmac.new(self.sk.encode('utf-8'),
                             signing_str.encode('utf-8'), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode('utf-8')
        return signature_b64

    def verify_signature(self, method, url, headers, body=None):
        if 'x-ca-signature' not in headers:
            raise SignatureAuthException("无权访问，签名未提供")

        timestamp = int(headers.get('x-ca-timestamp', 0))
        current_time = int(time.time())
        if current_time - timestamp > self.timeout:
            raise SignatureAuthException('请求已失效')
        if 'x-ca-none' not in headers or len(headers['x-ca-none']) != 32:
            raise SignatureAuthException("X-Ca-None参数格式错误")

        expected_signature = headers['x-ca-signature']
        # 特殊处理，本地请求
        if (is_internal_ip(self.request_ip) or self.nginx_proxy == True) and expected_signature == 'local':
            return True

        signature = self.generate_signature(
            method, url, headers, body)
        return expected_signature == signature
