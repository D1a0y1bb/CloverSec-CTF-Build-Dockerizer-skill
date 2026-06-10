# 使用官方PHP Apache镜像作为基础镜像
FROM php:8.1-apache

# 设置工作目录
WORKDIR /var/www/html

# 复制PHP文件到容器中
COPY 1.php /var/www/html/

# 设置文件权限
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

# 启用Apache mod_rewrite模块
RUN a2enmod rewrite

# 暴露80端口
EXPOSE 80

# 启动Apache服务
CMD ["apache2-foreground"]