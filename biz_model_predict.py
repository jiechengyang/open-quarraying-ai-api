#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'yang yang'

from asyncio import Task
import json
import os
from time import time

import aiohttp
from biz_dict import findTaskTypeDict
from components.models import App, TaskResult
import khandy
from biz_exceptions import ModelPredictException
from components.apis import BIZ_CODE_TASK_MODEL_PREDICT_LOCAL_IMAGE_NOT_FOUND, BIZ_CODE_TASK_MODEL_PREDICT_MODEL_ERROR, BIZ_CODE_TASK_MODEL_PREDICT_MODEL_NOT_FOUND, BIZ_CODE_TASK_MODEL_PREDICT_PARAMS_ERROR
from biz_helper import PUBLIC_PATH, STATIC_PATH, UPLOAD_PATH, add_biz_error_log, get_current_date, get_currnet_timestamp, bfb, is_valid_url, sort_dict_list
import plantid
from insectid import InsectDetector, InsectIdentifier
import cv2
import urllib.request
import numpy as np


'''
模型预测识别助手
'''

FONT_PATH = os.path.join(STATIC_PATH, 'fonts/SIMSUN.ttf')

'''
ai识别任务处理类
'''


class TaskPredictProcessor:
    def __init__(self, task):
        self.task = task
        self.__data_handlers = {
            'plant_img': self.plant_predict_image_stream,
            'plant_url': self.plant_predict_image_url,
            'insect_img': self.insect_predict_image_stream,
            'insect_url': self.insect_predict_image_url
        }

    '''
    根据识别功能处理数据
    '''
    async def process_data(self, data_type):
        if data_type in self.__data_handlers:
            # TODO: 暂时取消部分校验：目前项目逻辑是成功上传后才能到调用这里
            handler = self.__data_handlers[data_type]
            return await handler()
        else:
            raise ModelPredictException(
                message='未有可识别的模型', code=BIZ_CODE_TASK_MODEL_PREDICT_MODEL_NOT_FOUND)

    def __create_best_result_image(self, results, image):
        if not len(results):
            return None, '', '', ''
        if max(image.shape[:2]) > 1080:
            image = khandy.resize_image_long(image, 1080)
        best_match_result = results[0]
        _, best_match_val_percentage_format = bfb(
            best_match_result['probability'])
        text = '{}: {}'.format(
            best_match_result['name'], best_match_val_percentage_format)
        image = khandy.draw_text(
            image, text, (10, 10), font=FONT_PATH, font_size=24)
        save_dir, sub_save_dir = make_task_result_image_upload_path(
            self.task.task_type)
        new_filename = f'{str(get_currnet_timestamp())}_{self.task.task_uuid}.jpg'
        relative_path = f'{sub_save_dir}/{new_filename}'
        save_path = os.path.join(save_dir, new_filename)
        cv2.imwrite(save_path, image)

        return best_match_result['probability'], best_match_result['code'], best_match_result['name'], relative_path
    '''
      植物识别处理
    '''
    async def __plant_predict(self, is_url=False):
        if is_url:
            with urllib.request.urlopen(self.task.img_url) as response:
                image_data = response.read()
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            file_path = os.path.join(PUBLIC_PATH, self.task.img_local_path)
            plant_identifier = plantid.PlantIdentifier()
            image = khandy.imread_cv(file_path)
        if image is None:
            raise ModelPredictException(
                message='待识别图片解析失败：图片格式错误', code=BIZ_CODE_TASK_MODEL_PREDICT_LOCAL_IMAGE_NOT_FOUND)
        outputs = plant_identifier.identify(image, topk=5)
        if max(image.shape[:2]) > 1080:
            image = khandy.resize_image_long(image, 1080)
        if outputs['status'] == 0:
            # best_match_result = outputs['results'][0]
            # _, best_match_val_percentage_format = bfb(
            #     best_match_result['probability'])
            # text = '{}: {}'.format(
            #     best_match_result['chinese_name'], best_match_val_percentage_format)
            # image = khandy.draw_text(
            #     image, text, (10, 10), font=FONT_PATH, font_size=24)
            # save_dir, sub_save_dir = make_task_result_image_upload_path(
            #     self.task.task_type)
            # new_filename = f'{str(get_currnet_timestamp())}_{self.task.task_uuid}.jpg'
            # relative_path = f'{sub_save_dir}/{new_filename}'
            # save_path = os.path.join(save_dir, new_filename)
            # cv2.imwrite(save_path, image)
            target_results = self.__quarrying_parse_results(outputs['results'])
            # best_match_result['probability'], best_match_result['code'], best_match_result['name'], relative_path
            best_match_val, best_match_class_code, best_match_class_text, relative_path = self.__create_best_result_image(
                target_results, image)
            return dict(
                results=target_results,
                save_img_path=relative_path,
                best_match_score=best_match_val,
                best_match_class_text=best_match_class_text,
                best_match_class_code=best_match_class_code
            )

    '''
      昆虫识别处理
    '''
    async def __insect_predict(self, is_url=False):
        detector = InsectDetector()
        identifier = InsectIdentifier()
        if is_url:
            with urllib.request.urlopen(self.task.img_url) as response:
                image_data = response.read()
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            file_path = os.path.join(PUBLIC_PATH, self.task.img_local_path)
            image = khandy.imread(file_path)
        if image is None:
            raise ModelPredictException(
                message='待识别图片解析失败：图片格式错误', code=BIZ_CODE_TASK_MODEL_PREDICT_LOCAL_IMAGE_NOT_FOUND)
        if max(image.shape[:2]) > 1280:
            image = khandy.resize_image_long(image, 1280)
        image_for_draw = image.copy()
        image_height, image_width = image.shape[:2]
        boxes, confs, classes = detector.detect(image)
        result_list = []
        best_match_score = 0
        best_match_class_code = None
        best_match_class_text = ''
        for box, conf, class_ind in zip(boxes, confs, classes):
            box = box.astype(np.int32)
            box_width = box[2] - box[0] + 1
            box_height = box[3] - box[1] + 1
            if box_width < 30 or box_height < 30:
                continue
            cropped = khandy.crop_or_pad(image, box[0], box[1], box[2], box[3])
            results = identifier.identify(cropped)
            result_list.append(results)
            prob = results[0]['probability']
            _, best_match_val_percentage_format = bfb(prob)
            if prob < 0.10:
                text = '未知'
            else:
                text = '{}: {}'.format(
                    results[0]['chinese_name'], best_match_val_percentage_format)
            if best_match_score < prob:
                best_match_score = prob.tolist() if type(prob) == np.float32 else prob
                best_match_class_code = results[0]['latin_name']
                best_match_class_text = results[0]['chinese_name']
            position = [box[0] + 2, box[1] - 20]
            position[0] = min(max(position[0], 0), image_width)
            position[1] = min(max(position[1], 0), image_height)
            cv2.rectangle(image_for_draw,
                          (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
            image_for_draw = khandy.draw_text(image_for_draw, text, position,
                                              font=FONT_PATH, font_size=15)

        save_dir, sub_save_dir = make_task_result_image_upload_path(
            self.task.task_type)
        new_filename = f'{str(get_currnet_timestamp())}_{self.task.task_uuid}.jpg'
        relative_path = f'{sub_save_dir}/{new_filename}'
        save_path = os.path.join(save_dir, new_filename)
        cv2.imwrite(save_path, image_for_draw)
        target_results = self.__quarrying_insect_parse_results(result_list)
        # print('sorted:', sort_dict_list(target_results, 'probability', True))
        return dict(
            results=target_results,
            save_img_path=relative_path,
            best_match_score=best_match_score,
            best_match_class_text=best_match_class_text,
            best_match_class_code=best_match_class_code
        )

    '''
      识别上传的植物图片
    '''
    async def plant_predict_image_stream(self):
        return await self.__plant_predict()
    '''
      识别上传的植物图片url
    '''
    async def plant_predict_image_url(self):
        return await self.__plant_predict(True)

    '''
      识别上传的昆虫图片
    '''
    async def insect_predict_image_stream(self):
        return await self.__insect_predict()

    '''
      识别上传的昆虫图片url
    '''
    async def insect_predict_image_url(self):
        return await self.__insect_predict(True)
    '''
      解析格式化识别的植物结果（对应采石匠服务）
    '''

    def __quarrying_parse_results(self, results):
        if not len(results):
            return []
        items = []
        for result in results:
            if type(result['probability']) == np.float32:
                probability = result['probability'].tolist()
            else:
                probability = result['probability']
            item = dict(crop_type='common', crop_type_name='通用', code=result['latin_name'],
                        name=result['chinese_name'], probability=probability)
            items.append(item)
        return sort_dict_list(items, 'probability', True)
    '''
      解析格式化识别的昆虫结果（对应采石匠服务）
    '''

    def __quarrying_insect_parse_results(self, result_list):
        if not len(result_list):
            return []
        items = []
        for results in result_list:
            for result in results:
                if type(result['probability']) == np.float32:
                    probability = result['probability'].tolist()
                else:
                    probability = result['probability']
                item = dict(crop_type='common', code=result['latin_name'],
                            name=result['chinese_name'], probability=probability)
                items.append(item)
        return sort_dict_list(items, 'probability', True)


'''
发送结果给应用客户端接收的接口地址
'''


async def send_task_result_hock(hock_url, data):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        await session.post(hock_url, json=data, headers={'Content-Type': 'application/json'})

'''
ai 识别
'''


async def ai_predict(task: Task):
    file_path = None
    # print('ai_predict:', task)
    if not task.img_local_path and not task.img_url:
        raise ModelPredictException(
            message='缺少必要参数:img_local_path 或者 img_url', code=BIZ_CODE_TASK_MODEL_PREDICT_PARAMS_ERROR)
    if task.img_local_path:
        file_path = os.path.join(PUBLIC_PATH, task.img_local_path)
        if not os.path.isfile(file_path):
            # 可以有更严谨的判断
            raise ModelPredictException(
                message='未找到识别的图片：图片为暂存到临时目录', code=BIZ_CODE_TASK_MODEL_PREDICT_LOCAL_IMAGE_NOT_FOUND)
        data_type = '%s_img' % task.task_type
    else:
        data_type = '%s_url' % task.task_type
    ident_module = get_ident_by_task_type(task.task_type)
    app = await App.findByAppKey(task.app_key)
    task_type_dict = findTaskTypeDict(task.task_type)
    try:
        processeor = TaskPredictProcessor(task)
        result = await processeor.process_data(data_type)
        if not result['best_match_score']:
            await add_biz_error_log('task_result', 'model_predict', "图像分类识别失败", result)
            raise ModelPredictException(
                message='识别失败，未识别到结果', code=BIZ_CODE_TASK_MODEL_PREDICT_MODEL_ERROR)
        task_result = TaskResult(
            app_key=task.app_key,
            task_id=task.id,
            task_uuid=task.task_uuid,
            task_type=task.task_type,
            ident_module=ident_module,
            task_name=task.task_name,
            status=1,
            class_code=result['best_match_class_code'],
            class_name=result['best_match_class_text'],
            class_score=result['best_match_score'],
            result=json.dumps(result, ensure_ascii=False),
            result_img_path=result['save_img_path']
        )
        await task_result.save()
        task.status = 2
        task.finshed_at = time()
        await task.update()
        send_result = dict(
            app_key=task_result.app_key,
            task_uuid=task_result.task_uuid,
            task_type=task_result.task_type,
            task_type_name='' if task_type_dict == None else task_type_dict['value'],
            ident_module=task_result.ident_module,
            task_name=task_result.task_name,
            status=task_result.status,
            add_user_id=task['user_id'],
            class_code=task_result.class_code,
            class_name=task_result.class_name,
            class_score=task_result.class_score,
            result_img_url=get_task_result_best_class_result_img_url(
                result['save_img_path']),
            result=result
        )
        await send_task_result(app, send_result)
        send_result = None
        return result
    except Exception as e:
        msg = "图像分类识别失败：" + str(e)
        task_result = TaskResult(
            app_key=task.app_key,
            task_id=task.id,
            task_uuid=task.task_uuid,
            task_type=task.task_type,
            ident_module=ident_module,
            task_name=task.task_name,
            status=0,
            class_code='',
            class_score=0,
            class_name='',
            result='',
            result_img_path=''
        )
        await task_result.save()
        task.status = 3
        await task.update()
        send_result = dict(
            app_key=task_result.app_key,
            task_uuid=task_result.task_uuid,
            task_type=task_result.task_type,
            task_type_name='' if task_type_dict == None else task_type_dict['value'],
            ident_module=task_result.ident_module,
            task_name=task_result.task_name,
            status=task_result.status,
            add_user_id=task['user_id'],
            class_code='',
            class_name='',
            class_score=0,
            result_img_url='',
            result=''
        )
        await send_task_result(app, send_result)
        send_result = None
        await add_biz_error_log('task_result', 'model_predict', msg, task)
        raise ModelPredictException(
            message=msg, code=BIZ_CODE_TASK_MODEL_PREDICT_MODEL_ERROR)
    finally:
        # 清理上传的文件
        if file_path:
            os.unlink(file_path)


async def send_task_result(app, send_result):
    if app is not None and is_valid_url(app.result_hock):
        print('send task result hock')
        await send_task_result_hock(app.result_hock, send_result)
        return False
    return True


def get_task_result_best_class_result_img_url(result_img_path):
    from config.bapp import configs
    img_url_host = configs.img_url

    return f"{img_url_host}{result_img_path}"


def get_ident_by_task_type(task_type):
    return 'QueryMan'


'''
创建识别结果文件存储目录
'''


def make_task_result_image_upload_path(func_code):
    sub_dir = f'task_result/{func_code}/{get_current_date()}'
    dir = f'{UPLOAD_PATH}/{sub_dir}'
    not os.path.isdir(dir) and os.makedirs(dir, mode=0o755, exist_ok=True)

    return dir, sub_dir
