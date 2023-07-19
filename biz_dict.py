#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Yang Yang'

'''
任务状态；0=已生成；1=识别处理中；-1=已取消；2=识别成功；3=识别失败
'''
ai_task_status_dict = [
    {
        'key': 0,
        'value': '已生成'
    },
    {
        'key': 1,
        'value': '识别处理中'
    },
    {
        'key': -1,
        'value': '已取消'
    },
    {
        'key': 2,
        'value': '识别成功'
    },
    {
        'key': 3,
        'value': '识别失败'
    }
]

ai_task_type_dict = [
    {
        'key': 'plant',
        'value': '植物识别'
    },
    {
        'key': 'insect',
        'value': '昆虫识别'
    }
]

'''
每日每个应用授权最大请求识别任务数字典

'''
ai_task_day_max_request_num_dict = [
    {
        'key': 'plant',
        'value': 2000
    },
    {
        'key': 'insect',
        'value': 2000
    }
]


def findDictByKey(dicts, targetVal, dKeyFlag='key'):
    for dict in dicts:
        if dict[dKeyFlag] == targetVal:
            return dict
    return None


def findTaskDayMaxRequestNum(func_code):
    target_dict = findDictByKey(ai_task_day_max_request_num_dict, func_code)
    if not target_dict:
        return 0

    return target_dict['value']


def findTaskTypeDict(func_code):
    return findDictByKey(ai_task_type_dict, func_code)


def findTaskStatusDict(status):
    dict = findDictByKey(ai_task_status_dict, status)
    return '' if dict == None else dict['value']
