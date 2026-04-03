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
