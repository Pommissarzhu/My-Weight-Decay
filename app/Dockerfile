FROM python:3.10-slim

WORKDIR /app

# 替换为阿里云镜像源 (Debian 11 bullseye)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# 安装必要的系统依赖 (OpenCV 需要 glib)
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# 复制依赖并安装
COPY requirements.txt .
# 使用阿里云 PyPI 镜像加速 pip 安装
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt

# 这里的 COPY . . 在开发时会被 docker-compose 的 volume 覆盖，但在生产构建时很有用
COPY . .

# 确保 static/uploads 文件夹存在
RUN mkdir -p static/uploads
