# ---- legacy-helper-v2 / linux-qemu-v1 兼容片段 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# helper 合同要求脚本可执行；初始 flag 文件按合同决定是否保留
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
