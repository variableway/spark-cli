# Batch Update
Batch update is a feature that allows users to update multiple github repo folder in one command

## Task 1: Implement batch update command

1. create a subcommand for git to commit, and push all the repos in current folder to github
2. Use Case:
    1. in Current Folder, there are several github repos
    2. Some changes in these folders
    3. use spark git push-all to push all changes in git repo to github

verification:
1. in ../innate folder
2. using spark git push-all to push all changes in to github
3. if the current repo is not a github repo, ignore the push action, then go to next
4. if conflict occurs, then prompt user to resolve the conflict, and continue other repo's push action


## Task 2: 加入git 初始化远程项目命令

1. 进入当前的目录，运行 spark git init
2. 实际运行了， git init, spark git config, 然后检查当前项目中是否子目录已经是github仓库了，如果是就把这个仓库变成git submodule 添加到当前的git仓库中
3. 关键github 远程仓库，gh repo create 这个方式，默认名称就是当前目录名称，用户就是可以配置，默认在config文件中配置
4.  最后添加.gitignore,添加常见的忽略文件，比如node_modules, dist, .vscode, .idea, python环境，go环境,.envw, .gitkeep, etc，mac 相关，比如.DS_Store, .macOS, etc
