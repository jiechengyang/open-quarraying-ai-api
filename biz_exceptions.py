#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'yang yang'

'''
业务异常
'''


from components.apis import APIError


class TaskBizException(APIError):
    def __init__(self, data=dict(), message='', code=...):
        super().__init__('biz:task', data, message, code)


class ModelPredictException(APIError):
    def __init__(self, data=dict(), message='', code=...):
        super().__init__('biz:model_predict', data, message, code)
