# Init Skills

These Tasks for Init command

## Task 1: init docs structure 

automatically create docs folder structure, the folder structure is as follow:

```sh
.
├── Agents.md
├── analysis 
├── features
├── index.md
├── quick-start
├── README.md
├── spec
├── tips
└── usage
```

## Task 2: Init docmd setting in current folder

docmd is a zero configuration documentation generator. 
[docmd](https://docs.docmd.io/)
[docmd-github](https://github.com/docmd-io/docmd)

1. 请按照上面docs structure 初始化docmd setting
2. 如果当前目录的docs和上面docs structure不一致，那就按照当前docs目录初始化docmd setting
3. 如果没有全局安装docmd就全局安装
4. 初始化好GitHub Action 让docs可以部署到github-pages

## Task 3: add docs sub-command to init 

- add docs sub-command for spark-cli to init docs structure based on:
```sh
.
├── Agents.md
├── analysis 
├── features
├── index.md
├── quick-start
├── README.md
├── spec
├── tips
└── usage
```
- the command is like ```spark docs init```
- add sub-command ```spark docs site``` to use init docmd site configuration
- make sure ```spark docs site``` to use the docs folder as root folder ,and docmd.config.js using
current git repo's title and url.