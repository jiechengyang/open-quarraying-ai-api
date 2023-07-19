# 基础镜像
FROM python:3.10
# FROM ubuntu:20.04

ARG db_password=Aa123456
ARG db_name
ARG WORK_DIR=/quarrying_ai
# 设置工作目录
WORKDIR ${WORK_DIR}

# 复制项目文件到容器中
COPY . ${WORK_DIR}
# 卷：将宿主机目录映射到容器中，使用
# VOLUME ["/var/lib/mysql", "/var/log/mysql", "/var/log/supervisor", "/quarrying_ai/public/uploads"]
# 复制数据库配置文件和修改配置
# sed -i "s/'user': 'root'/'user': '$db_user'/" config/app_override.py && \
RUN sed -i "s/'password': 'root'/'password': '$db_password'/" config/app_override.py && \
  sed -i "s/'db': 'quarrying_ai'/'db': '$db_name'/" config/app_override.py
RUN cat config/app_override.py

# 更新软件包列表并安装必要的工具
# RUN apt-get update && \
#   apt-cache search mysql-server
# 安装 supervisor MySQL 客户端和服务.7   OpenGL 的系统依赖库
# RUN apt-get update && \
#   DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends && \
#   apt-get install -y build-essential &&\
#   apt-get install -y ca-certificates &&\
#   apt-get install -y curl &&\
#   apt-get install -y python3.10 &&\
#   apt-get install -y python3-pip &&\
#   apt-get install -y net-tools && \
#   apt-get install -y supervisor && \
#   apt-get install -y mariadb-client && \
#   apt-get install -y mariadb-server && \
#   apt-get install -y libgl1-mesa-glx && \
#   apt-get clean && \
#   rm -rf /var/lib/apt/lists/*


# 可以安装调试使用 apt-get install -y net-tools && \
RUN apt-get update && \
  apt-get install -y supervisor && \
  apt-get install -y mariadb-client && \
  apt-get install -y mariadb-server && \
  apt-get install -y libgl1-mesa-glx && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# 设置 Python 3.10 为默认的 Python 版本
RUN ln -sf /usr/bin/python3.10 /usr/bin/python
# 修改 pip 镜像源为阿里云
# RUN mkdir /root/.pip && \
#   echo "[global]\ntrusted-host = mirrors.aliyun.com\nindex-url = https://mirrors.aliyun.com/pypi/simple" > /root/.pip/pip.conf
# 安装依赖
RUN pip install --upgrade pip && \
  pip install -r requirements.txt

# 设置 MySQL 配置文件并启动 MySQL 服务
COPY private/conf/mysql/my.cnf /etc/mysql/my.cnf
RUN mkdir -p /var/log/mysql && \
  chown -R mysql:mysql /var/log/mysql && \
  mkdir -p /var/run/mysqld && \
  chown -R mysql:mysql /var/run/mysqld && \
  mkdir -p /var/data/mysql && \
  chown -R mysql:mysql /var/data/mysql

# 创建启动 MySQL 和导入数据库的脚本
RUN echo "#!/bin/bash \n\
  files=\`ls /var/data/mysql\` \n\
  if [ -z \"\$files\" ];then \n\
  db_password=\"${db_password}\" \n\
  /usr/sbin/mysqld --initialize  --datadir=/var/data/mysql > /var/log/mysql/mysqld.log 2>&1 \n\
  MYSQLOLDPASSWORD=$(grep 'temporary password' /var/log/mysql/mysqld.log | awk '{print $NF}')\n\
  /usr/sbin/mysqld & \n\
  echo \"[client] \\\n  password=\"\${MYSQLOLDPASSWORD}\" \\\n user=root\" > ~/.my.cnf \n\
  sleep 4s \n\
  mariadb_version=\$(/usr/bin/mysql -V | awk '{print $5}' | awk -F ',' '{print $1}') \n\
  version_compare() { \n\
  test \"\$(printf '%s\\n' \"\$@\" | sort -V | head -n 1)\" != \"\$1\";  \n\
  } \n\
  if version_compare \"\${mariadb_version}\" \"10.11.4\"; then  \n\
  /usr/bin/mysql --connect-expired-password -e \"alter user 'root'@'localhost' identified by '\${db_password}';update mysql.global_priv set host='%' where user='root' && host='localhost';flush privileges;\" \n\
  else \n\
  /usr/bin/mysql --connect-expired-password -e \"SET PASSWORD FOR 'root'@'localhost' = PASSWORD('\${db_password}');update mysql.global_priv set host='%' where user='root' && host='localhost';flush privileges;\" \n\
  fi \n\
  /usr/bin/mysql -u root -p\"${db_password}\" -e \"CREATE DATABASE IF NOT EXISTS ${db_name};\" \n\
  /usr/bin/mysql -u root -p\"${db_password}\" ${db_name} -e \"source /quarrying_ai/backup/quarrying_ai.sql\" \n\
  echo \"[client] \\\n  password=\"\${db_password}\" \\\n user=root\" > ~/.my.cnf \n\
  while sleep 3600 \n\
  do \n\
  result=$((1+1)) \n\
  done \n\
  else \n\
  rm -rf /var/run/mysqld/mysql.sock.lock \n\
  /usr/sbin/mysqld \n\
  fi" > /mysql.sh \
  && chmod +x /mysql.sh

# RUN cat /mysql.sh

# 创建 supervisord 配置文件
RUN echo "[supervisord] \n\
  nodaemon=true \n\
  user = root \n\
  \n\
  [unix_http_server] \n\
  file=/var/run/supervisor.sock \n\
  \n\
  [include] \n\
  files = /etc/supervisor/conf.d/*.conf\n\
  [program:mysql] \n\
  command=/bin/sh /mysql.sh \n\
  autorestart=true \n\
  \n\
  stdout_logfile          = /var/log/supervisor/mysql_out.log \n\
  \n\
  stderr_logfile          = /var/log/supervisor/mysql_err.log \n\
  [program:quarrying_ai] \n\
  \n\
  command     = python ${WORK_DIR}/app.py \n\
  \n\
  directory   = ${WORK_DIR}/ \n\
  user        = root \n\
  \n\
  startsecs   = 3 \n\
  \n\
  redirect_stderr         = true \n\
  \n\
  stdout_logfile_maxbytes = 50MB \n\
  \n\
  stdout_logfile_backups  = 10 \n\
  \n\
  stdout_logfile          = /var/log/supervisor/quarrying_ai_out.log \n\
  \n\
  stderr_logfile          = /var/log/supervisor/quarrying_ai_err.log"> /etc/supervisor/conf.d/supervisord.conf

RUN chmod +x ${WORK_DIR}/docker-entrypoint.sh

# ENTRYPOINT ["/bin/bash", "${WORK_DIR}/docker-entrypoint.sh"]
# 暴露容器端口
EXPOSE 3535 3306
# 容器启动命令
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]