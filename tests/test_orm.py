'''
python -m unittest tests.test_orm

python -m tests.test_orm
'''

from components.orm import Model
from components.models import User, next_id
import unittest
import sys
import asyncio
import time
import aiohttp
import os
import random
import string
from typing import Any, Coroutine
import xml.etree.ElementTree as ET
import hashlib
import aiomysql
# import pytest

# 获取当前工作目录
current_dir = os.getcwd()



#
# 运行1：python tests/test_orm.py 运行2： cd tests && python test_orm.py 都可以
sys.path.insert(0, sys.path[0]+"/../")
# 这样运行：cd tests && python test_orm.py
# sys.path.append('..')
# sys.path.insert(0, os.path.join(current_dir, 'components'))
# for i in sys.path:
#     print(i)


# global _db

def hash_password(password):
    # 创建一个新的 hashlib.md5 对象
    hasher = hashlib.md5()

    # 将密码转换为字节串并进行哈希计算
    hasher.update(password.encode('utf-8'))

    # 获取哈希值的十六进制表示
    hashed_password = hasher.hexdigest()

    return hashed_password


def generate_account_name():
    characters = string.ascii_letters + string.digits + '_'
    max_length = 20
    account_name = ''.join(random.choice(characters)
                           for _ in range(random.randint(4, max_length)))
    return account_name


def generate_email():
    domain = ['gmail.com', 'yahoo.com', '163.com', 'outlook.com', 'qq.com']
    max_length = 10
    username_length = random.randint(1, max_length)
    username = ''.join(random.choice(string.ascii_lowercase + string.digits)
                       for _ in range(username_length))
    email = f"{username}@{random.choice(domain)}"
    return email


def generate_avatar_url(w=150, h=150):
    base_url = "https://www.bing.com"
    image_path = "/HPImageArchive.aspx?format=xml&idx=0&n=1&mkt=en-US"
    avatar_url = f"{base_url}{image_path}"

    # 添加查询参数来指定图片大小
    avatar_url += f"&width={w}&height={h}"

    return avatar_url


async def get_bing_image_url(w=150, h=150):
    xml_url = generate_avatar_url(w, h)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(xml_url) as response:
                xml_data = await response.text()
    except aiohttp.ClientError as e:
        print("请求出错:", str(e))
        return None

    try:
        root = ET.fromstring(xml_data)
        url_base = root.find(".//urlBase").text
        image_url = f"https://www.bing.com{url_base}_{w}x{h}.jpg"
        return image_url
    except ET.ParseError as e:
        print("解析 XML 出错:", str(e))
        return None


class OrmTestCase(unittest.IsolatedAsyncioTestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
    # async def setUp(self) -> None:
    #     loop = asyncio.get_event_loop()
    #     self.pool = await init_db_pool(loop,
    #                               host='127.0.0.1',
    #                               port=3306,
    #                               user='root',
    #                               password='root',
    #                               db='plant_insect_ai',
    #                               charset='utf8mb4')
    # async def tearDown(self) -> None:
    #     # 关闭连接池
    #     self.pool.close()
    #     await self.pool.wait_closed()
    # @classmethod
    # async def setUpClass(cls):
    #     print('111')
    #     await init_db_pool(host='127.0.0.1', port=3306, user='root', password='root', db='plant_insect', charset='utf8mb4')

    def setUp(self) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.pool = None

    '''
为什么使用 asyncio.get_event_loop() 是正确的，
而使用 self.loop 会报错，可能是因为 unittest 
在运行异步测试用例时，会使用自己的事件循环来管理异步操作。在 IsolatedAsyncioTestCase 中，通过重写 asyncSetUp 方法，
unittest 会自动创建一个新的事件循环，并将其设置为当前事件循环。因此，在 asyncSetUp 方法中使用 asyncio.get_event_loop() 
可以获取到正确的事件循环
    '''
    async def asyncSetUp(self) -> Coroutine[Any, Any, None]:
        loop = asyncio.get_event_loop()
        _db = Model.init_db_proxy(loop)
        self._db = _db
        await _db.make_pool(host='127.0.0.1',
                            port=3306,
                            user='root',
                            password='root',
                            db='plant_insect_ai',
                            charset='utf8mb4')

    async def asyncTearDown(self) -> Coroutine[Any, Any, None]:
        self._db.pool.close()
        await self._db.pool.wait_closed()

    def tearDown(self) -> None:
        self.loop.run_until_complete(self.asyncTearDown())
        self.loop.close()

    async def test_create_user(self):
        # loop = asyncio.get_event_loop()
        # pool = await init_db_pool(loop,
        #                           host='127.0.0.1',
        #                           port=3306,
        #                           user='root',
        #                           password='root',
        #                           db='plant_insect_ai',
        #                           charset='utf8mb4')
        avatar = await get_bing_image_url()
        if not avatar:
            avatar = 'http://demo.rockoa.com/upload/face/1.jpg'
        pwd = '12345678'
        pwd = hash_password(pwd)
        user = User(name=generate_account_name(),
                    email=generate_email(), password=pwd, image=avatar)
        res = await user.save()

        # pool.close()
        # await pool.wait_closed()
        self.assertGreaterEqual(res, 0)

    async def test_find_one_user(self):
        id = '001687599757426dc090d4c6ccd4a999a856301b4cd554a000'
        user = await User.find(id)
        print('user:', user)

        self.assertEqual(user.id, id)

    async def test_find_all_users(self):
        users = await User.findAll(' 1 AND name = ?', ['Admin'], orderBy='created_at DESC', limit=(0, 5))

        self.assertEqual(len(users), 0)

    async def test_count_user(self):
        count = await User.count('id', where='1')

        self.assertGreaterEqual(count, 1)

    async def test_update_user(self):
        id = '001687599757426dc090d4c6ccd4a999a856301b4cd554a000'
        user = await User.find(id)
        old_name = user.name
        old_email = user.email
        user.name = generate_account_name()
        user.email = generate_email()
        user.admin = 3
        res = await user.update()

        self.assertNotEqual(old_name, user.name)
        self.assertNotEqual(old_email, user.email)

    async def test_delete_user(self):
        pass
        # id = '001687599761202ab74d967be394fd4810d380484324c51000'
        # user = await User.find(id)
        # res = await user.remove()

        # self.assertEqual(res, 1)
    async def test_batch_create_user(self):
        avatar = 'http://demo.rockoa.com/upload/face/1.jpg'
        pwd = '12345678'
        pwd = hash_password(pwd)
        # rows = [
        #     (next_id(), generate_email(), pwd, 0, generate_account_name() + '_1', avatar,time.time(),time.time()),
        #     (next_id(), generate_email(), pwd, 0, generate_account_name() + '_2', avatar,time.time(),time.time())
        # ]
        models = [
            User(name=generate_account_name(),
                 email=generate_email(), password=pwd, image=avatar),
            User(name=generate_account_name(),
                 email=generate_email(), password=pwd, image=avatar)
        ]
        # await User.batch_create(rows)
        res = await User.batch_create_by_model(models)

        self.assertEqual(res, len(models))

    async def test_conn(self):
        conn, cursor = await self._db.make_conn(host='127.0.0.1',
                                                port=3306,
                                                user='root',
                                                password='root',
                                                db='plant_insect_ai',
                                                charset='utf8mb4')
        await cursor.execute("SELECT * FROM user")
        r = await cursor.fetchall()
        # print('r:', r)
        await cursor.close()
        conn.close()
        self.assertIsInstance(conn, aiomysql.connection.Connection) and self.assertIsInstance(
            cursor, aiomysql.cursors.Cursor)

    async def test_transaction(self):
        avatar = 'http://demo.rockoa.com/upload/face/1.jpg'
        pwd = '12345678'
        pwd = hash_password(pwd)
        user = User(name=generate_account_name(),
                    email=generate_email(), password=pwd, image=avatar)
        conn = await self._db.get_pool_conn()
        try:
            await self._db.begin_transaction(conn)
            save_res = await user.save(conn)
            old_email = user.email
            user.email = 'dev@aa.com'
            update_res = await user.execute(f"update user set email='{user.email}' where email = ?;", (old_email), conn)
            user = await user.find(user.id, conn)
            await self._db.commit_transaction(conn)
            print('save_res:', save_res)
            print('update_res:', update_res)
        except Exception as e:
            await self._db.rollback_transaction(conn)
            raise e
        finally:
            '''
            release() 方法：该方法用于将连接返回给连接池，以便在需要时可以再次使用。调用 release() 方法后，连接对象将返回到连接池中，并标记为可用状态，以供其他代码获取和使用。这种方式可以实现连接的重用，避免频繁地创建和关闭连接。

close() 方法：该方法用于显式关闭连接，即将连接彻底关闭并释放相关资源。调用 close() 方法后，连接将不再可用，不能再进行数据库操作。如果需要再次使用数据库连接，需要重新从连接池获取一个新的连接。

使用 release() 方法可以更好地管理连接的生命周期和连接池的资源，以提高性能和效率。而使用 close() 方法则表示当前操作完成后不再需要该连接，可以立即释放相关资源。

一般情况下，建议在不需要连接对象时使用 release() 方法将连接返回给连接池，以便其他代码可以重用该连接。只有在确定不再需要连接时，才使用 close() 方法来显式关闭连接。这样可以更好地管理连接池的资源，并提供更好的性能和可伸缩性。
            '''
            # conn.close()
            self._db.pool.release(conn)

        print('update_after_user:', user)
        self.assertEqual(user.email, 'dev@aaa.com')


if __name__ == '__main__':
    # print('111')
    unittest.main()
