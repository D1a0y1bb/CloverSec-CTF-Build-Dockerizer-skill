# java-jar-basic

最小 Java JAR 示例。目录包含：

- `src/Main.java`：源码
- `app.jar`：可直接运行的 JAR
- `challenge.yaml`：渲染输入

## 重新生成 app.jar

```bash
mkdir -p build/classes
javac -d build/classes src/Main.java
printf 'Main-Class: Main\n' > build/MANIFEST.MF
jar cfm app.jar build/MANIFEST.MF -C build/classes .
```
