# BaseUnit SSHD Example

This example packages a minimal OpenSSH service directory with `stack=baseunit`.

- Family: `sshd`
- Variant style: Debian Bookworm + `openssh-server`
- Service port: `22`
- Start command: `mkdir -p /var/run/sshd /etc/ssh && ssh-keygen -A && exec /usr/sbin/sshd -D -e -p 22`

You can render a similar directory with:

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component sshd \
  --variant bookworm \
  --output /tmp/baseunit-sshd-render
```
