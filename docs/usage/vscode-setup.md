# VS Code 设置说明

本项目的 `.vscode` 目录包含了一套完整的配置，旨在为 Go 语言开发提供无缝的体验。

## 核心配置文件

### 1. [tasks.json](../.vscode/tasks.json)
定义了项目常用的构建和测试任务，并与 `Makefile` 深度集成。
- **默认构建任务 (`Ctrl+Shift+B`)**: 执行 `make build`。
- **默认测试任务**: 执行 `make test`。
- **BDD 测试**: 执行 `make test-bdd`。
- **清理任务**: 执行 `make clean`。

### 2. [launch.json](../.vscode/launch.json)
预设了多种调试场景：
- **Debug Main**: 调试主程序入口 (`main.go`)。
- **Debug Current File**: 调试当前选中的 `.go` 文件。
- **Debug Test Current File**: 调试当前选中的测试文件。
- **Debug All Tests**: 运行并调试项目中的所有测试。
- **Attach to Delve**: 附加到已经在运行的 Delve 调试器。

### 3. [settings.json](../.vscode/settings.json)
优化了编辑器行为：
- **自动格式化**: 保存时自动执行 `go fmt` 和 `goimports`。
- **Linting**: 开启了基于 `golangci-lint` 的实时代码检查。
- **Code Lens**: 在代码中直接显示测试运行和引用的快捷链接。

## 环境要求
- **VS Code 扩展**: 必须安装 [Go for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=golang.Go)。
- **工具链**: 建议安装 `make` 以获得最佳体验。
