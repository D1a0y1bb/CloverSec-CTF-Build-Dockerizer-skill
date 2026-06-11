# bundle-custom-explicit

自定义 Bundle 示例：用户显式提供 `base_image`、`install_commands`、`start_commands`、端口和服务清单。

```bash
python3 ../../scripts/render_bundle.py --config bundle.yaml --output /tmp/bundle-custom-explicit
python3 ../../scripts/validate_bundle.py --bundle-dir /tmp/bundle-custom-explicit
bash ../../scripts/validate.sh /tmp/bundle-custom-explicit/Dockerfile /tmp/bundle-custom-explicit/start.sh /tmp/bundle-custom-explicit/challenge.yaml
```

本示例不做版本求解，也不自动选择服务安装方式。
