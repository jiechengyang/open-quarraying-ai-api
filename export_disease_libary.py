#!/usr/bin/env python3
# coding:utf-8

__author__ = 'yang yang'

'导入病虫害库'

import asyncio
import os
import json
from config.bapp import configs

from components.models import DiseaseLibary
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))


async def main(loop):
    _db = DiseaseLibary.init_db_proxy(loop)
    await _db.make_pool(**configs.db)
    json_path = os.path.join(ROOT_PATH, f'private/disease_libary.json')
    assert os.path.exists(
        json_path), "file: '{}' dose not exist.".format(json_path)
    with open(json_path, "r", encoding='utf-8') as f:
        disease_items = json.load(f)
    await DiseaseLibary.static_execute(sql='Truncate Table `disease_libary`')
    models = []
    num = 0
    for disease in disease_items:
        en_name = disease['disease_code'].split('_')[-1]
        models.append(DiseaseLibary(
            crop_type=disease['crop_code'], code=disease['disease_code'], cn_name=disease['disease_name'], en_name=en_name, order_num=num))
        num += 1
    res = await DiseaseLibary.batch_create_by_model(models)
    print('成功导入:', res)
    _db.pool.close()
    await _db.pool.wait_closed()

if __name__ == '__main__':
    # 获取EventLoop:
    loop = asyncio.get_event_loop()
    # 执行coroutine
    loop.run_until_complete(main(loop))
    loop.close()
