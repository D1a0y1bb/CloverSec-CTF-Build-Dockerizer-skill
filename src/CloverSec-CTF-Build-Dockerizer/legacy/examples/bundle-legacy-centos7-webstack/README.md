# bundle-legacy-centos7-webstack

Bundle/Recipe input for the fixed CentOS 7 + Python 3.9 + MySQL 5.7 + Redis 5 prototype.

```bash
python3 ../../scripts/render_bundle.py --config bundle.yaml --output /tmp/bundle-legacy-centos7-webstack
python3 ../../scripts/validate_bundle.py --bundle-dir /tmp/bundle-legacy-centos7-webstack
```
