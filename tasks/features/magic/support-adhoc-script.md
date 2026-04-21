# Task 1: Support Adhoc script in command line

## 描述

为 spark CLI 添加一个新的子命令 script，用来执行自定义的脚本，

1. 脚本的内容可以在 `~/.spark.yaml` 中配置。可以多个脚本，每个脚本都有一个唯一的名称。

## 例如

```yaml
spark:
  scripts:
    - name: update-readme
      content: |
        #!/bin/bash
        # 更新README.md文件
        echo "更新README.md文件"
```
2. 脚本内容也可以是写好的shell，sh脚本文件，制动路径就可以
3. ~/.spark.yaml 文件中指定脚本的路径，默认为当前目录下的scripts/ 目录
4. 可以不在spark.yaml定义任何命令，直接在命令行中执行 `spark script run <script-name>` 即可执行对应的脚本。是从scripts/ 目录中读取脚本内容。同时支持MAC，Linux，Windows
5. sh脚本可能支持参数话，这个script run也需要支持参数
5. 支持list 操作，可以获取所有的scripts内容


## 验收标准

- [ ] 新命令命名为 `spark script run <script-name>`
- [ ] 读取 `~/.spark.yaml` 中的 `scripts` 配置
- [] 用一个例子来实现：比如常见批量目录：
  ```sh
  drwxr-xr-x  9 patrick staff 288 Apr  3 10:01 .
drwxr-xr-x 22 patrick staff 704 Apr  3 11:58 ..
drwxr-xr-x  2 patrick staff  64 Apr  3 10:01 analysis
drwxr-xr-x  2 patrick staff  64 Apr  3 10:00 config
-rw-r--r--  1 patrick staff 407 Apr  3 09:18 example-feature.md
drwxr-xr-x  4 patrick staff 128 Apr  3 11:47 features
drwxr-xr-x  2 patrick staff  64 Apr  3 10:01 mindstorm
drwxr-xr-x  2 patrick staff  64 Apr  3 10:01 planning
drwxr-xr-x  2 patrick staff  64 Apr  3 10:01 prd
  ```
- [] 一个例子验证复制文件，复制example-feature.md到features/ 目录下，并且按照参数修改名称



