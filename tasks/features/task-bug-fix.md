# Task 1: Spark Task Sub Command Bug fix 

## 描述

1. after make build and make install, the command is still using the old verion for spark not the latest spark version
2. `spark task create "make script issue" --content` 这个命令使用的时候出现一个问题，就是example-feature.md文件内容没有复制到make script issue.md文件中。
   同时文件名需要把描述中的空格变成-
3. create的时候吧content参数的内容也，复制到新创建目录的## 描述 section下面
4. 

## 验收标准

- [ ] 添加对应的单元测试
- [ ] 更新 README 使用说明
- [] 更新AGENTS.md文件

