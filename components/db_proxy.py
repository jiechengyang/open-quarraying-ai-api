#!/usr/bin/env python3
# coding:utf-8

import aiomysql
'db pool'

__author__ = 'yang yang'

import logging
# logging.basicConfig(level=logging.INFO)
# 设置日志级别和日志格式
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class DbPoolProxy(object):
    pool: aiomysql.Pool

    def __init__(self, loop) -> None:
        self.__loop = loop

    async def make_pool(self, **kw):
        self.pool = await aiomysql.create_pool(
            host=kw.get('host', 'localhost'),
            port=kw.get('port', 3306),
            user=kw['user'],
            password=kw['password'],
            db=kw['db'],
            charset=kw.get('charset', 'utf8'),
            autocommit=kw.get('autocommit', True),
            maxsize=kw.get('maxsize', 10),
            minsize=kw.get('minsize', 1),
            loop=self.__loop
        )

    async def make_conn(self, **kw):
        conn = await aiomysql.connect(
            host=kw.get('host', 'localhost'),
            port=kw.get('port', 3306),
            user=kw['user'],
            password=kw['password'],
            db=kw['db'],
            charset=kw.get('charset', 'utf8'),
            autocommit=kw.get('autocommit', True),
            loop=self.__loop
        )
        cur = await conn.cursor()
        return (conn, cur)

    async def select(self, sql, args, size=None):
        logging.info('sql:%s, params:%s', sql, args)
        async with self.pool.acquire() as conn:
            return await self.conn_select(conn, sql, args, size)

    async def conn_select(self, conn: aiomysql.Connection, sql, args,  size=None):
        # 返回字典列表：DictCursor
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

    async def get_pool_conn(self) -> aiomysql.Connection:
        try:
            return await self.pool.acquire()
        except Exception as e:
            raise e

    async def execute(self, sql: str, args):
        # logging.info('sql:%s, params:%s', sql, args)
        async with self.pool.acquire() as conn:  # aiomysql.Connection
            return await self.conn_execute(conn, sql, args)

    async def conn_execute(self, conn: aiomysql.Connection, sql: str, args):
        try:
            cur = await conn.cursor(aiomysql.DictCursor)
            await cur.execute(sql.replace('?', '%s'), args or ())

            affected = cur.rowcount
            if sql.startswith('insert') or sql.startswith('INSERT'):
                affected = cur.lastrowid

            await cur.close()
        except BaseException as e:
            raise e
        return affected

    async def execute_many(self, sql, rows):
        logging.info('sql:%s, rows:%s', sql, rows)
        async with self.pool.acquire() as conn:
            try:
                cur = await conn.cursor(aiomysql.DictCursor)
                sql = sql.replace('?', '%s')
                await cur.executemany(sql, rows)
                affected = cur.rowcount
                await cur.close()
            except BaseException as e:
                raise e

            return affected

    # 开启事物
    async def begin_transaction(self, conn: aiomysql.Connection):
        await conn.begin()

    # 提交事物
    async def commit_transaction(self, conn: aiomysql.Connection):
        await conn.commit()

    # 回滚事物
    async def rollback_transaction(self, conn: aiomysql.Connection):
        await conn.rollback()
