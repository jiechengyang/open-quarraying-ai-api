#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
JSON API definition.
'''

import json
import logging
import inspect
import functools

BIZ_CODE_OK = 0
BIZ_CODE_ERROR = 101
BIZ_CODE_VALUE_ERROR = 400001
BIZ_CODE_NOT_FOUND = 404001
BIZ_CODE_FORBIDDEN = 403001
BIZ_CODE_APP_EXPIRED = 403100
BIZ_CODE_APP_DISABLED = 403101
BIZ_CODE_APP_NOT_EXIST = 403102
BIZ_CODE_AK_SK_AUTH_FAILED = 403103
BIZ_CODE_APP_FUNC_LIMITED = 403104
BIZ_CODE_TASK_REACHED_DAY_LIMIT = 500101
BIZ_CODE_TASK_NOT_FOUND = 404101
BIZ_CODE_TASK_MODEL_PREDICT_PARAMS_ERROR = 500201
BIZ_CODE_TASK_MODEL_PREDICT_LOCAL_IMAGE_NOT_FOUND = 500202
BIZ_CODE_TASK_MODEL_PREDICT_MODEL_NOT_FOUND = 500203
BIZ_CODE_TASK_MODEL_PREDICT_EASY_DL_CLIENT_ACCESS_TOKEN_EMPTY = 500204
BIZ_CODE_TASK_MODEL_PREDICT_EASY_DL_CLIENT_IMAGE_BASE64_ERROR = 500205
BIZ_CODE_TASK_MODEL_PREDICT_EASY_DL_CLIENT_IMAGE_URL_ERROR = 500206
BIZ_CODE_TASK_MODEL_PREDICT_MODEL_IMAGE_EXT_ERROR = 500207
BIZ_CODE_TASK_MODEL_PREDICT_MODEL_IMAGE_SIZE_ERROR = 500208
BIZ_CODE_TASK_MODEL_PREDICT_MODEL_ERROR = 500209


class Page(object):
    '''
    Page object for display pages.
    '''

    def __init__(self, item_count, page_index=1, page_size=10):
        '''
        Init Pagination by item_count, page_index and page_size.

        >>> p1 = Page(100, 1)
        >>> p1.page_count
        10
        >>> p1.offset
        0
        >>> p1.limit
        10
        >>> p2 = Page(90, 9, 10)
        >>> p2.page_count
        9
        >>> p2.offset
        80
        >>> p2.limit
        10
        >>> p3 = Page(91, 10, 10)
        >>> p3.page_count
        10
        >>> p3.offset
        90
        >>> p3.limit
        10
        '''
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + \
            (1 if item_count % page_size > 0 else 0)
        if (item_count == 0) or (page_index > self.page_count):
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index
            self.offset = self.page_size * (page_index - 1)
            self.limit = self.page_size
        self.has_next = self.page_index < self.page_count
        self.has_previous = self.page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__


class APIError(Exception):
    '''
    the base APIError which contains error(required), data(optional) and message(optional).
    '''

    def __init__(self, error, data='', message='', code=BIZ_CODE_ERROR):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message
        self.code = code


class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The data specifies the error field of input form.
    '''

    def __init__(self, field, message='', code=BIZ_CODE_VALUE_ERROR):
        super(APIValueError, self).__init__(
            'value:invalid', field, message, code)


class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The data specifies the resource name.
    '''

    def __init__(self, field, message='', code=BIZ_CODE_NOT_FOUND):
        super(APIResourceNotFoundError, self).__init__(
            'value:notfound', field, message, code)


class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''

    def __init__(self, message='', code=BIZ_CODE_FORBIDDEN):
        super(APIPermissionError, self).__init__(
            'permission:forbidden', 'permission', message, code)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
