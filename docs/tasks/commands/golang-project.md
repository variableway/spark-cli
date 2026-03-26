# Key Points

1. Go Project Dep Management 
    - `go mod tidy`: 自动添加代码中使用的依赖，并删除未使用的依赖。
    - `go mod vendor`: 将所有依赖项复制到项目的 `vendor` 目录中。
    - `go get <package>`: 下载并安装指定的包或依赖。
    - `go list -m all`: 列出当前项目的所有依赖模块。
2. How to Add Go dep, and How to Solve network issue for download go dep 
    - `go get <package>`: 下载并安装指定的包或依赖。
    - 解决网络问题：设置代理或使用镜像。
3. Go Project Layout
    - 推荐使用 [Go 项目布局](https://github.com/golang-standards/project-layout) 规范。
    - 包含 `cmd`, `internal`, `pkg`, `test` 等目录。
4. Different Golang Project Type
    - 命令行工具（CLI）
    - 库（Library）
    - 服务（Service）
    - 网站（Web Application）
5. 如何选择 Golang 项目类型
    - 根据项目的功能和规模选择合适的项目类型。
    - 命令行工具（CLI）：用于执行简单的任务。
    - 库（Library）：提供可重用的代码。
    - 服务（Service）：运行在服务器上的应用。
    - 网站（Web Application）：提供用户交互的 Web 应用。
6. 如何组织 Golang 项目
    - 遵循 [Go 项目布局](https://github.com/golang-standards/project-layout) 规范。
    - 组织代码，将不同的功能模块放在不同的目录中。
    - 保持代码的可维护性和可扩展性。
7. Golang 建立要求


```
1. 核心技术能力
语言精通：扎实的Go语言基础，深入理解Go Runtime、并发原语、内存模型、GC（垃圾回收）机制。
框架与工具：熟练使用Web框架（如 Gin, Beego, Echo）、ORM框架（如 GORM, Xorm）。
后端经验：2-4年以上后端开发经验，有C++/Java/Python/PHP等背景者通常也可转岗。
网络与数据：深入理解 TCP/IP、HTTP/HTTPS、UDP、DNS 等网络协议。
工程能力：熟悉 Linux 操作系统，熟练使用 Shell 脚本、Git/GitHub。 
DJI
DJI
 +2
2. 系统与架构能力
高并发：具备设计高并发、高可用、低延迟服务的能力。
分布式：熟悉分布式架构、消息队列（Kafka, RabbitMQ）、缓存（Redis, Memcached）。
数据存储：熟悉 MySQL 数据库设计、SQL 性能优化及数据结构、算法基础。 
Linux Foundation
Linux Foundation
 +2
3. 学历与经验
学历：本科及以上学历，计算机、软件工程、数学等相关专业。
工作经验：通常要求2-4年以上经验；高级工程师/专家岗位通常需要3-5年以上大型互联网系统开发经验。 
BOSS直聘
BOSS直聘
 +5
4. 加分项
参与过开源项目，有源码阅读或贡献经验。
有IoT（物联网）、云原生（Docker, Kubernetes）开发经验。
有良好的文档编写能力、写技术博客或活跃于技术社区。 
DJI
DJI
 +2
5. 软技能
优秀的逻辑思维能力和问题排查/性能调优能力。
团队协作能力、责任心强，对代码质量有高标准（代码洁癖）
```