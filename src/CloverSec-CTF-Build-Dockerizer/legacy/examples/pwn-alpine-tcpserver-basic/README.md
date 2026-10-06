# pwn-alpine-tcpserver-basic

- 目的：覆盖 Pwn 在 Alpine 基础镜像下的 `tcpserver` 兼容路径。
- 关键点：`ctf.xinetd` 端口与 `EXPOSE` 对齐，`start.sh` 可在无 xinetd 时回退 tcpserver。
