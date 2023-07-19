#!/usr/bin/env python3
# coding:utf-8

__author__ = 'yang yang'

import time
import uuid

import aiomysql
from .orm import Model, StringField, BooleanField, FloatField, TextField, IntegerField, EnumField


def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)


class User(Model):
    __table__ = 'user'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)


class App(Model):
    __table__ = 'app'

    id = IntegerField(primary_key=True)
    app_key = StringField(ddl='varchar(16)')
    app_secret = StringField(ddl='varchar(32)')
    app_name = StringField(ddl='varchar(64)')
    expired_at = FloatField(default=0)
    status = BooleanField()
    funcs = StringField(ddl='varchar(100)', default='*')
    result_hock = StringField(ddl='varchar(255)', default='')
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)

    @classmethod
    async def findByAppKey(cls, app_key, conn: aiomysql.Connection = None):
        ' find object by app key. '
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `%s`=?' % (cls.__select__, 'app_key'), [app_key], 1)
        else:
            rs = await cls._db.select('%s where `%s`=?' % (cls.__select__, 'app_key'), [app_key], 1)
        if len(rs) == 0:
            return None

        return cls(**rs[0])


class Task(Model):
    __table__ = 'task'

    id = IntegerField(primary_key=True)
    task_uuid = EnumField()
    task_type = StringField(ddl='varchar(16)')
    task_name = StringField(ddl='varchar(100)')
    app_key = StringField(ddl='varchar(16)')
    img_local_path = StringField(ddl='varchar(255)')
    img_url = StringField(ddl='varchar(255)')
    req_params = StringField(ddl='varchar(200)')
    req_ip = StringField(ddl='varchar(32)')
    req_user_agent = StringField(ddl='varchar(255)')
    status = BooleanField()
    remark = StringField(ddl='varchar(255)')
    finshed_at = FloatField()
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)

    @classmethod
    async def findByUUID(cls, uuid, conn: aiomysql.Connection = None):
        ' find object by uuid. '
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `task_uuid`=? LIMIT 1' % (cls.__select__), [uuid])
        else:
            rs = await cls._db.select('%s where `task_uuid`=? LIMIT 1' % (cls.__select__), [uuid])
        if len(rs) == 0:
            return None

        return cls(**rs[0])


class TaskResult(Model):
    __table__ = 'task_result'

    id = IntegerField(primary_key=True)
    app_key = StringField(ddl='varchar(16)')
    task_id = IntegerField(ddl='int(11', default=0)
    task_uuid = StringField(ddl='varchar(32)')
    task_type = StringField(ddl='varchar(16)')
    ident_module = StringField(ddl='varchar(16)')
    task_name = StringField(ddl='varchar(255)')
    status = BooleanField()
    class_code = StringField(ddl='varchar(16)')
    class_name = StringField(ddl='varchar(255)')
    class_score = FloatField(default=0)
    result = TextField()
    result_img_path = StringField(ddl='varchar(255)')
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)

    @classmethod
    async def findByTaskUUID(cls, task_uuid, conn: aiomysql.Connection = None):
        ' find object by task uuid. '
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `task_uuid`=? ORDER BY id DESC LIMIT 1' % (cls.__select__), [task_uuid])
        else:
            rs = await cls._db.select('%s where `task_uuid`=? ORDER BY id DESC  LIMIT 1' % (cls.__select__), [task_uuid])
        if len(rs) == 0:
            return None

        return cls(**rs[0])


class Log(Model):
    __table__ = 'log'
    id = IntegerField(primary_key=True)
    user_id = IntegerField()
    module = StringField(ddl='varchar(32)')
    action = StringField(ddl='varchar(100)')
    message = TextField()
    data = TextField()
    ip = StringField(ddl='varchar(100)')
    level = StringField(ddl='char(10)')
    created_at = FloatField(default=time.time)


class Token(Model):
    __table__ = 'biz_token'
    id = IntegerField(primary_key=True)
    place = StringField(ddl='varchar(32)')
    _key = StringField(ddl='varchar(32)')
    data = TextField()
    expired_time = IntegerField(ddl="int(10)")
    times = IntegerField(ddl="int(10)")
    remaining_times = IntegerField(ddl="int(10)")
    created_at = FloatField(default=time.time)

    @classmethod
    async def findByPlaceAndKey(cls, place, key, conn: aiomysql.Connection = None):
        ' find object by place and key. '
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `place`=? AND `_key`=? order by `id` DESC LIMIT 1' % (cls.__select__), [place, key])
        else:
            rs = await cls._db.select('%s where `place`=? AND `_key`=? order by `id` DESC LIMIT 1' % (cls.__select__), [place, key])
        if len(rs) == 0:
            return None

        return cls(**rs[0])


class CropLibary(Model):
    __table__ = 'crop_libary'
    id = IntegerField(primary_key=True)
    code = StringField(ddl='varchar(32)')
    name = StringField(ddl='varchar(255)')
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)


class DiseaseLibary(Model):
    __table__ = 'disease_libary'
    id = IntegerField(primary_key=True)
    crop_type = StringField(ddl='varchar(32)', default='common')
    code = StringField(ddl='varchar(32)')
    cn_name = StringField(ddl='varchar(255)')
    en_name = StringField(ddl='varchar(255)')
    order_num = IntegerField(default=0)
    prevent_ways = TextField(default='')
    created_at = FloatField(default=time.time)
    updated_at = FloatField(default=time.time)

    @classmethod
    async def findByCode(cls, code, conn: aiomysql.Connection = None):
        ' find object by code. '
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `code`=? ORDER BY id DESC LIMIT 1' % (cls.__select__), [code])
        else:
            rs = await cls._db.select('%s where `code`=? ORDER BY id DESC  LIMIT 1' % (cls.__select__), [code])
        if len(rs) == 0:
            return None

        return cls(**rs[0])
