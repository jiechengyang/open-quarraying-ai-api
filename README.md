# 基于aiohttp开发quarrying api 

这是一个使用 aiohttp 构建的 quarrying api,用于植物、昆虫、名人脸识别

## 安装

1. 克隆仓库：

    ```shell
    git clone git@github.com:jiechengyang/open-quarraying-ai-api.git
    ```

2. 进入项目目录

    ```shell
    cd your-project

    ```

3. 创建虚拟环境（可选但推荐,python版本3.10以上，推荐3.10）

   ```shell
    python -m venv venv
    source venv/bin/activate

   ```
   `or`
   ```shell
    conda create -n py3.10 python=3.10 -y
    conda activate py3.10

   ```
4. 安装依赖
   
   ```shell
   pip install -r requirements.txt
   ```

## 配置

1. 将 config/app_default.py 文件重命名为 app_override.py。
2. 打开 config/app_orverride.py 文件，并根据您的需求更新配置设置

## 导入数据库
1. 新建数据库：`quarrying_ai` (名称同config下db配置)
2. 导入`backup/quarrying_ai.sql`文件（该文件保留最新的结构）
## 使用

1. ~~生成ai app 应用端授权码~~（默认db存在，生成新授权在使用）

   ```shell
        your_python make_ai_app.py
   ```
2. ~~导入作物病虫库~~（默认db存在）
   ```shell
        your_python export_disease_libary.py
   ```
3. 启动：
   - 开发模式监听启动

    ```shell
    # linux
    python pymonitor.py app.py
    # linux or
    # ./pymonitor.py app.py
    # windows
    # python .\pymonitor.py .\app.py
    ```

   - 直接启动

    ```shell
    python app.py
    ```
4. 停止: `python app.py -c stop`
5. 状态： `sudo python app.py -c status`
6. 打开浏览器，访问 `http://localhost:{your_port}` 以访问 Web 应用程序。

## 部署
### ~~fabric 打包~~
- 暂未完成
- 见 > [tests/test_fabfile.py](tests/test_fabfile.py)

### 打包为可执行文件
1. 安装PyInstaller
   ```shell
   pip install pyinstaller
   ```
2. 切换到包含您的Python脚本的目录,使用PyInstaller创建可执行文件
   ```shell
   pyinstaller --onefile --paths ./config --add-data "./public:public" app.py
   ```
3. 运行dist目录中的可执行文件
### 手动部署

  同上述安装流程
  
### docker

   - 构建镜像
  
  ```shell
  docker build  --build-arg db_name=byt_quarrying_ai -t quarrying_ai:latest .

  ```
  - 运行容器
  
  ```shell
  docker run -d --name quarrying_ai -p 3535:3535 13306:3306 quarrying_ai:latest
  # 关闭数据库映射：不暴露3306端口，启动 -p 3535:3535
  # 使用卷，打开dockerfile的 volume [] 注释，运行
  #docker run -v /host/mysql:/var/lib/mysql -v /host/mysql/logs:/var/log/mysql -v /host/supervisor/logs:/var/log/supervisor -v /host/static:/path/to/static/files -d --name quarrying_ai -p 3535:3535 quarrying_ai:latest
  ```

  - 查看容器列表
  
  ```shell
  docker ps
  ```

  - 停止容器

```shell
docker stop container_name

```

  - 删除容器
  
```shell
docker rm container_name

```

  - 查看镜像列表
  
```shell
docker images

```

  - 删除镜像

```shell
docker rmi image_name:tag

```

  - 进入容器

```shell
docker exec -it container_name /bin/bash

```


## 单元测试
  - orm测试：`python -m unittest tests/test_orm`
## 已完成功能

- 植物识别
- 昆虫识别
- 完成接口签名验证
- 完成命令生成应用授权信息
- 创建识别任务接口
- 获取识别任务接口
- 获取识别任务明细接口
- docker部署
- 打包可执行文件

## 待完成功能
- 接入名人人像识别
- 接入通用人脸识别
- 优化合并 植物、昆虫、名人人像识别代码目录
- 构建docker-compose

## 接口
   见wiki
## 问题
- 图片地址
  1. 在没有反向代理的情况下，图片地址默认是客户端请求的站点地址：`{scheme}://{host}:{?port}/uploads/`
  2. 如果使用反向代理的情况下，请在`app/app_override.py`里面配置`img_url`来覆盖
  3. 如果使用了cdn，请在`app/app_override.py`里面配置`img_url`来覆盖
- 跨域
   [教程](https://www.cnblogs.com/marvintang1001/p/12470142.html)

```
 import aiohttp_cors
 from aiohttp import web

 app = web.Application()
 app.router.add_post("/offer", offer)
    
 cors = aiohttp_cors.setup(app, defaults={
   "*": aiohttp_cors.ResourceOptions(
        allow_credentials=True,
        expose_headers="*",
        allow_headers="*"
    )
  })

  for route in list(app.router.routes()):
    cors.add(route)
```
## 项目结构

项目结构如下所示:

```tree

quarrying_ai_api/
  ├── app.py
  ├── coroweb.py
  ├── make_ai_app.py
  ├── routes.py
  ├── requirements.txt
  ├── README.md
  ├── .gitignore
  ├── backup/
  └── components/
      ├── __init__.py
      ├── .gitignore
      ├── models.py
      ├── orm.py
      ├── db_proxy.py
      └── apis.py
  └── config/
      ├── .gitignore
      ├── app_default.py
      ├── app_override.py
      └── config.py
  └── public/
      ├── uploads/
      ├── static/
      └── templates/
  └── tests/
      ├── .gitignore
      ├── __init__.py
      ├── ....
      └── test_orm.py
```

- app.py：Web 应用程序的主入口点。
- config/：应用程序设置的配置文件目录：具体参考app_default.py来定制修改app_override.py。
- requirements.txt：项目所需的依赖项列表。
- components/：组件包
- coroweb.py：不同的请求处理程序。
- make_ai_app.py：创建ai app 应用客户端。
- routes.py：路由定义和动态路由自动解析处理程序。
- public/：存储 HTML 模板的目录、静态资源目录、上传目录

根据项目需求，您可以自由修改项目结构，添加或删除文件。

## 体验
- [采石匠官网](https://www.quarryman.cn/insect)
## 站在巨人的肩膀
 - [quarrying](https://github.com/quarrying)
 ...

## 联系合作
 - 合作：kefu@boyuntong.com
 - 问题：yangjiecheng@boyuntong.com