# BaseUnit Redis Example

This example packages a minimal Redis service directory with `stack=baseunit`.

- Family: `redis`
- Variant style: official `redis:7.2-alpine`
- Service port: `6379`
- Start command: `redis-server --protected-mode no --bind 0.0.0.0`

You can render a similar directory with:

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --output /tmp/baseunit-redis-render
```
