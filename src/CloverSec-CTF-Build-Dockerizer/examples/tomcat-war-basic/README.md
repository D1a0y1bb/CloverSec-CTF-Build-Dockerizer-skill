# tomcat-war-basic

最小 Tomcat WAR 示例。目录包含：

- `webroot/index.jsp`
- `ROOT.war`（可直接部署）
- `challenge.yaml`

## 重新生成 ROOT.war

```bash
jar cf ROOT.war -C webroot .
```
