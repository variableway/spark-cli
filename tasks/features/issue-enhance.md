# Task 1: 把GITHUB tasks flow 变成一个skill

## 描述

- 把GITHUB tasks flow 变成一个skill
- 这个GITHUB tasks flow ，放到spark-skills中去
- 把spark-task-init-skill也放到spark-skill中去
- 更新spark-skills.md文件
- 更新AGENTS.md文件
- spark-skills目录变成一个全新的github仓库去创建和管理
- 确认当前spark-skills目录下的所有文件都已提交到github仓库，同时还可以被全局使用
- spark-skill目录准备做一个个人skill集合的仓库，用于存储个人的skill，和一些使用的skill/

# Task 2: 测试github-task-workflow

如果github task workflow安装到全局，是否还起作用呢：
通过下面这个操作测试一下：
1. 执行spark task create "docs-check" --content "check docs for errors or outdated" 
2. 执行上一步的这个任务
3. 最后确认issue是否创建完成