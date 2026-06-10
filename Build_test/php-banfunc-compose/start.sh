#!/bin/bash

# PHP测试环境快速启动脚本
echo "正在构建PHP测试环境..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker未运行，请先启动Docker"
    exit 1
fi

# 停止并删除已存在的容器
echo "清理旧容器..."
docker-compose down 2>/dev/null

# 构建并启动容器
echo "构建并启动容器..."
docker-compose up --build -d

# 等待容器启动
echo "等待服务启动..."
sleep 5

# 检查容器状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ PHP测试环境启动成功!"
    echo "📋 访问地址: http://localhost:8080/1.php"
    echo "📋 测试命令: http://localhost:8080/1.php?cmd=phpinfo();"
    echo "📋 停止服务: docker-compose down"
    echo "📋 查看日志: docker-compose logs -f"
else
    echo "❌ 容器启动失败，请检查日志:"
    docker-compose logs
fi