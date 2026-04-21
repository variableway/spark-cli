# Task：为 spark-cli 添加项目列表更新到README的命令

## 描述

为 spark CLI 添加一个新的子命令，添加项目列表更新到README的命令：
1. 读取所有该组织下的所有项目列表
2. 按照starred数量排序
3. 更新.github目录下的README.md文件,在Section Project List下面展示所有项目列表
4. 自动在.github 目录中git add ./git commit ./git push

## 验收标准

- [ ] 新命令命名为 `spark git update-org-status <org-name>`
- [ ] 读取当前组织下的所有项目列表
- [ ] 以表格形式输出.github目录下的README.md文件,按照starred数量排序，.github 目录下的README.md 更新在Section Project List下面就可以，其他README.md 文件内容可以无需更改，如果表格形式不好就用list的形式展示
- [ ] 添加对应的单元测试
- [ ] 更新 README 使用说明

## Task 2: 生成的结果文件直接修改.github仓库上面的README.md文件

- [] 支持参数话直接Update .github仓库上面的README.md文档，当然确保只更新更新在Section Project List这部分内容。
- [] 添加对应的单元测试
- [] 默认参数是直接udpate readme.md文件

## Task 3: Skill fro golang-cli-app

1. please give the code example of golang-cli-app skill for references
2. please provide install script for this skill for users
3. make sure tui version is easy to use
4. make sure the subcommand rule is easy to understand


## Task 4: move skill outside this project

1. move golang-cli-app skill outside of this project
2. make it looks like a real skill，then move to ../fire-skills/dev 目录