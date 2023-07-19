#!/usr/bin/env python3
# coding:utf-8
# 作者 yang yang
import asyncio
import logging

import aiomysql


from .db_proxy import DbPoolProxy


def log(sql, args=()):
    logging.info('SQL: %s' % sql)


def create_args_string(num):
    L = ['?' for n in range(num)]
    # for n in range(num):
    #     L.append('?')
    return ', '.join(L)


def init_db_proxy(loop) -> DbPoolProxy:
    # global _db
    _db = DbPoolProxy(loop)

    return _db


class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class EnumField(Field):
    def __init__(self, name=None, primary_key=False, default=None):
        super().__init__(name, 'enum', primary_key, default)


class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(255)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'tinyint', False, default)


class IntegerField(Field):

    def __init__(self,  name=None, primary_key=False, default=0, ddl='int(11)'):
        super().__init__(name, ddl, primary_key, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'double', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


'''
 元类
'''


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # 排除Model类本身:
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取table名称:
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 获取所有的Field和主键名:
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                # logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键:
                    if primaryKey:
                        raise RuntimeError(
                            'Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (
            primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(
            escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(
            map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (
            tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):
    _db = None

    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    @classmethod
    def init_db_proxy(cls, loop):
        cls._db = init_db_proxy(loop)

        return cls._db

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def set_db_proxy(self, db):
        self._db = db

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' %
                              (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        cls.check_db_is_init(cls)
        default_select = str(cls.__select__)
        columns = kw.get('columns', None)
        if columns is not None:
            if isinstance(columns, list):
                columns = ",".join([f'`{c}`' for c in columns])
            default_select = f"SELECT {columns} FROM {cls.__table__} "
        sql = [default_select]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await cls._db.select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        cls.check_db_is_init(cls)
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await cls._db.select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def count(cls, countField='*',  where=None, args=None):
        ' count by select and where. '
        cls.check_db_is_init(cls)
        sql = [f'SELECT COUNT({countField}) AS `total` FROM {cls.__table__}']
        if where:
            sql.append('where')
            sql.append(where)
        sql.append('LIMIT 1')
        rs = await cls._db.select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return 0
        return rs[0]['total']

    @classmethod
    async def find(cls, pk, conn: aiomysql.Connection = None):
        ' find object by primary key. '
        cls.check_db_is_init(cls)
        if isinstance(conn, aiomysql.Connection):
            rs = await cls._db.conn_select(conn, '%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        else:
            rs = await cls._db.select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None

        return cls(**rs[0])

    async def save(self, conn: aiomysql.Connection = None):
        self.check_db_is_init()
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        if isinstance(conn, aiomysql.Connection):
            rows = await self._db.conn_execute(conn, self.__insert__, args)
        else:
            rows = await self._db.execute(self.__insert__, args)
        if rows <= 0:
            logging.warning('Failed to insert record: after rows: ' % rows)
            return 0
        if 'id' in self:
            self['id'] = rows
        return rows

    async def update(self, conn: aiomysql.Connection = None):
        self.check_db_is_init()
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        if isinstance(conn, aiomysql.Connection):
            rows = await self._db.conn_execute(conn, self.__update__, args)
        else:
            rows = await self._db.execute(self.__update__, args)
        if rows != 1:
            logging.warning(
                'failed to update by primary key: affected rows: %s' % rows)
            return 0

        return rows

    async def remove(self, conn: aiomysql.Connection = None):
        self.check_db_is_init()
        args = [self.getValue(self.__primary_key__)]
        if isinstance(conn, aiomysql.Connection):
            rows = await self._db.conn_execute(conn, self.__delete__, args)
        else:
            rows = await self._db.execute(self.__delete__, args)
        if rows != 1:
            logging.warning(
                'failed to remove by primary key: affected rows: %s' % rows)

            return 0

        return rows

    @classmethod
    async def batch_create(self, rows):
        self.check_db_is_init()
        placeholders = ', '.join(['%s'] * len(rows[0]))
        insert_statement = f"INSERT INTO {self.__table__} VALUES ({placeholders})"
        rows = await self._db.execute_many(insert_statement, rows)
        print('batch create rows:', rows)
        return rows

    @classmethod
    async def batch_create_by_model(cls, models):
        cls.check_db_is_init(cls)
        argsList = []
        for model in models:
            args = list(map(model.getValueOrDefault, model.__fields__))
            args.append(model.getValueOrDefault(model.__primary_key__))
            argsList.append(args)
            args = []
        rows = await cls._db.execute_many(cls.__insert__, argsList)

        return rows

    async def execute(self, sql, args=None, conn: aiomysql.Connection = None):
        self.check_db_is_init()
        if conn:
            return await self._db.conn_execute(conn, sql, args)
        return await self._db.execute(sql, args)

    @classmethod
    async def static_execute(cls, sql, args=None, conn: aiomysql.Connection = None):
        cls.check_db_is_init(cls)
        if conn:
            return await cls._db.conn_execute(conn, sql, args)
        return await cls._db.execute(sql, args)

    def check_db_is_init(self):
        if self._db is None:
            raise IOError('ORM db not init')
