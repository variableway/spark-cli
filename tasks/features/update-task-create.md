# Task： 为 spark 添加或者修改新命令

## 描述

为 spark 添加或者修改新命令，主要是sub command是task的命令：
1. 新的task命令包含：
    1. `spark task init`: 创建所有的目前task目录和复制文件example-feature.md 到task目录，如果已经有task目录了，保留原来目录，然后在原来目录下目前task目录先的目录
    2. `spark task list`: 列出所有的feature目录下内容
    3. `spark task create <feature-name>`: 创建一个新的feature文件，文件名是<feature-name>.md，内容是example-feature.md的内容，但是文件名是<feature-name>.md，同时加上content参数，可以输入content内容，默认是空字符串。
    4. `spark task delete <feature-name>`: 删除指定的feature文件
    5. `spark task impl <feature-name>`: 执行指定的feature文件，使用kimi 的执行功能，执行feature文件的内容，同时让kimi cli可以调用github workflow 来执行feature文件的内容。同时需要能够自动完成这个feature内容，同时在tui或者terminal上展示所有的执行结果
    6. 创建一个skill，可以在其他目录中执行 `spark task init` 来执行task init 操作

## 验收标准

- [ ] 命令命名为 `spark task 。。。。。`
- [ ] 支持task init 操作
- [ ] 支持task list 操作
- [ ] 支持task create 操作
- [ ] 支持task delete 操作
- [ ] 支持task impl 操作
- [ ] 添加对应的单元测试
- [ ] 更新 README 使用说明
- []  可以通过创建一个skill的任务来验证spark task相关的以上所有操作


