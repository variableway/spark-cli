---
name: golang-cli-app
description: Go CLI 应用开发技能 - 提供 Cobra/Viper/PTerm/Bubble Tea 的代码示例、项目模板和最佳实践
type: skill
supported_agents:
  - claude-code
  - kimi
  - codex
  - opencode
---

# Golang CLI App Skill

使用 Go 构建 CLI 应用的代码模板和最佳实践参考。基于 [spark-cli](https://github.com/variableway/spark-cli) 项目提炼。

## 技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| CLI 框架 | [Cobra](https://github.com/spf13/cobra) | 命令定义、子命令、flag |
| 配置 | [Viper](https://github.com/spf13/viper) | YAML/ENV/flag 配置绑定 |
| TUI (基础) | [PTerm](https://github.com/pterm/pterm) | 彩色输出、表格、Spinner |
| TUI (交互) | [Bubble Tea](https://github.com/charmbracelet/bubbletea) | 交互式选择器、确认对话框 |
| 测试 | [Ginkgo/Gomega](https://onsi.github.io/ginkgo/) | BDD 风格测试 |

## 子命令规则

### 命令层级设计

```
app                          # 根命令
├── sub1 [action]            # 一级子命令 + 动作
│   └── sub1 action <args>   # 或嵌套子命令
├── sub2 [list|create|delete] # CRUD 风格
└── sub3 [--tui]             # 支持 TUI 模式
```

### 命名约定

1. **一级命令**用名词（`git`, `task`, `agent`）
2. **二级命令**用动词（`list`, `create`, `delete`, `update`, `sync`）
3. **Flag 命名**：`--long-name`（kebab-case），缩写 `-s`（单字母）
4. **配置键**：YAML 中 `snake_case`，struct tag 中 `camelCase`

### 代码示例：命令定义

```go
// cmd/git/git.go
package git

import "github.com/spf13/cobra"

var GitCmd = &cobra.Command{
    Use:   "git",
    Short: "Git repository management commands",
    Long: `Git commands for managing multiple repositories.

This includes:
- update: Update multiple git repositories
- mono: Mono repo management
- config: Configure git user for repository`,
}

func init() {
    // 子命令通过各自文件的 init() 注册
}
```

```go
// cmd/git/update.go
package git

import (
    "fmt"
    "github.com/spf13/cobra"
    "github.com/spf13/viper"
)

var updateCmd = &cobra.Command{
    Use:   "update",
    Short: "Update all repos to latest version",
    RunE: func(cmd *cobra.Command, args []string) error {
        path := viper.GetStringSlice("repo-path")
        // ... 业务逻辑
        fmt.Printf("Updating repos in %v\n", path)
        return nil
    },
}

func init() {
    GitCmd.AddCommand(updateCmd)
}
```

### 代码示例：Flag 与配置绑定

```go
// cmd/root.go
func init() {
    // Persistent flags - 子命令继承
    rootCmd.PersistentFlags().String("path", ".", "Repo directory")
    viper.BindPFlag("repo-path", rootCmd.PersistentFlags().Lookup("path"))

    // Local flags - 仅当前命令
    rootCmd.Flags().StringP("output", "o", "", "Output file")
}

// cmd/task.go
func init() {
    taskCmd.PersistentFlags().BoolVar(&useTUI, "tui", false, "Enable interactive TUI mode")
    taskCmd.PersistentFlags().StringVar(&taskDir, "task-dir", "", "Task directory")
    viper.BindPFlag("task_dir", taskCmd.PersistentFlags().Lookup("task-dir"))
}
```

## TUI 使用指南

### 两种 TUI 模式

| 模式 | 库 | 适用场景 | 复杂度 |
|------|-----|---------|--------|
| **CLI 模式**（默认） | PTerm | 彩色输出、表格、进度条 | 低 |
| **交互模式**（`--tui`） | Bubble Tea | 选择器、确认对话框 | 中 |

### PTerm 基础输出

```go
import "github.com/pterm/pterm"

// 基础消息
pterm.Info.Println("Processing...")
pterm.Success.Println("Done!")
pterm.Warning.Println("No items found.")
pterm.Error.Println("Something went wrong.")

// 表格
pterm.DefaultTable.WithHasHeader().WithData(pterm.TableData{
    {"Name", "Description", "Stars"},
    {"spark-cli", "CLI tool", "42"},
}).Render()

// 分段标题
pterm.DefaultSection.Println("Project List")

// Bullet List
pterm.DefaultBulletList.WithItems([]pterm.BulletListItem{
    {Level: 0, Text: "Item 1"},
    {Level: 0, Text: "Item 2"},
}).Render()

// Spinner
spinner, _ := pterm.DefaultSpinner.Start("Loading...")
// ... do work
spinner.Success("Loaded!")

// 交互确认
result, _ := pterm.DefaultInteractiveConfirm.Show("Continue?")
```

### Bubble Tea 交互选择器

```go
// internal/tui/selector.go
package tui

import (
    "fmt"
    "strings"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
)

var (
    selectedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("170")).Bold(true)
    itemStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
    titleStyle    = lipgloss.NewStyle().Foreground(lipgloss.Color("205")).Bold(true)
    quitStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
)

type SelectModel struct {
    items    []string
    cursor   int
    selected string
    title    string
    quitted  bool
}

func NewSelectModel(title string, items []string) SelectModel {
    return SelectModel{items: items, title: title}
}

func (m SelectModel) Init() tea.Cmd { return nil }

func (m SelectModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case tea.KeyMsg:
        switch msg.String() {
        case "ctrl+c", "q":
            m.quitted = true
            return m, tea.Quit
        case "up", "k":
            if m.cursor > 0 { m.cursor-- }
        case "down", "j":
            if m.cursor < len(m.items)-1 { m.cursor++ }
        case "enter", " ":
            m.selected = m.items[m.cursor]
            return m, tea.Quit
        }
    }
    return m, nil
}

func (m SelectModel) View() string {
    var b strings.Builder
    b.WriteString(titleStyle.Render(m.title))
    b.WriteString("\n\n")
    for i, item := range m.items {
        if m.cursor == i {
            b.WriteString(selectedStyle.Render("→ " + item))
        } else {
            b.WriteString(itemStyle.Render("  " + item))
        }
        b.WriteString("\n")
    }
    b.WriteString("\n")
    b.WriteString(quitStyle.Render("↑/↓: navigate, Enter: select, q: quit"))
    return b.String()
}

// 便捷函数
func SelectItem(title string, items []string) (string, error) {
    if len(items) == 0 {
        return "", fmt.Errorf("no items to select")
    }
    p := tea.NewProgram(NewSelectModel(title, items))
    m, err := p.Run()
    if err != nil { return "", err }
    model := m.(SelectModel)
    if model.WasQuitted() { return "", fmt.Errorf("selection cancelled") }
    return model.GetSelected(), nil
}
```

### 确认对话框

```go
// internal/tui/confirm.go
package tui

import (
    "fmt"
    tea "github.com/charmbracelet/bubbletea"
)

type ConfirmModel struct {
    message  string
    confirmed bool
    quitted  bool
}

func Confirm(message string) (bool, error) {
    p := tea.NewProgram(&ConfirmModel{message: message})
    m, err := p.Run()
    if err != nil { return false, err }
    return m.(*ConfirmModel).confirmed, nil
}
```

### TUI 集成模式（命令中使用）

```go
var useTUI bool

// 在 init() 中注册 flag
cmd.PersistentFlags().BoolVar(&useTUI, "tui", false, "Enable interactive TUI mode")

// 在 RunE 中分支
RunE: func(cmd *cobra.Command, args []string) error {
    if useTUI {
        return runTUI(args)
    }
    return runCLI(args)
}

func runCLI(args []string) error {
    // 简单的 CLI 逻辑
    name := args[0]
    pterm.Info.Printf("Processing %s...\n", name)
    return nil
}

func runTUI(args []string) error {
    // 交互式 TUI 逻辑
    items := []string{"option1", "option2", "option3"}
    selected, err := tui.SelectItem("Choose:", items)
    if err != nil {
        pterm.Info.Println("Cancelled.")
        return nil
    }
    pterm.Success.Printf("Selected: %s\n", selected)
    return nil
}
```

## 项目结构模板

```
my-cli/
├── main.go                    # 入口，调用 cmd.Execute()
├── go.mod
├── Makefile                   # build/test/lint 目标
├── cmd/                       # Cobra 命令定义
│   ├── root.go               # 根命令 + 配置加载
│   └── feature/              # 按功能分组
│       ├── feature.go        # 父命令
│       ├── action.go         # 子命令
│       └── action_test.go
├── internal/                  # 业务逻辑
│   ├── feature/              # 按领域拆分
│   │   ├── service.go
│   │   └── service_test.go
│   └── tui/                  # 共享 TUI 组件
│       ├── ui.go             # PTerm 封装
│       ├── selector.go       # Bubble Tea 选择器
│       └── confirm.go        # Bubble Tea 确认
├── docs/usage/               # 每个命令的使用文档
└── scripts/                  # 辅助脚本
```

## Makefile 模板

```makefile
BINARY_NAME=myapp
GO=go
INSTALL_DIR=~/.local/bin

.PHONY: build test lint clean

build: clean
	$(GO) build -ldflags="-s -w" -o $(BINARY_NAME) .
	@mkdir -p $(INSTALL_DIR)
	@cp $(BINARY_NAME) $(INSTALL_DIR)/$(BINARY_NAME)

test:
	$(GO) test ./... -v

lint:
	$(GO) vet ./...

clean:
	rm -f $(BINARY_NAME)
	$(GO) clean
```

## 配置文件模板

```go
// cmd/root.go
func initConfig() {
    home, _ := os.UserHomeDir()
    viper.AddConfigPath(home)
    viper.SetConfigName(".myapp")
    viper.SetConfigType("yaml")
    viper.AutomaticEnv()

    if err := viper.ReadInConfig(); err == nil {
        fmt.Fprintln(os.Stderr, "Using config:", viper.ConfigFileUsed())
    }
}
```

对应 `~/.myapp.yaml`:

```yaml
repo-path:
  - /path/to/repos
default-name: "value"
debug: false
```

## BDD 测试模板

```go
// internal/mypkg/service_suite_test.go
package mypkg_test

import (
    "testing"
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
)

func TestMyPkg(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "MyPkg Suite")
}
```

```go
// internal/mypkg/service_test.go
package mypkg_test

import (
    . "github.com/onsi/ginkgo/v2"
    . "github.com/onsi/gomega"
    "myapp/internal/mypkg"
)

var _ = Describe("Service", func() {
    Describe("DoSomething", func() {
        It("should work correctly", func() {
            result := mypkg.DoSomething("input")
            Expect(result).To(Equal("expected"))
        })
    })
})
```

## 安装

### macOS / Linux

```bash
# 项目级安装
./skills/golang-cli-app/scripts/install.sh --project

# 系统级安装
./skills/golang-cli-app/scripts/install.sh --system

# 仅安装到指定 agent
./skills/golang-cli-app/scripts/install.sh --system --agent claude-code
```

### Windows

```powershell
# 项目级安装
.\skills\golang-cli-app\scripts\install.ps1 -Project

# 系统级安装
.\skills\golang-cli-app\scripts\install.ps1 -System
```

## 参考项目

- [spark-cli](https://github.com/variableway/spark-cli) - 本技能的源项目
- [Cobra 官方文档](https://cobra.dev/)
- [Bubble Tea 教程](https://github.com/charmbracelet/bubbletea#tutorial)
- [PTerm 示例](https://github.com/pterm/pterm#examples)
