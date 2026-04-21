# TUI Patterns Reference

本文档详细说明 spark-cli 中使用的 TUI 模式，方便在构建新 CLI 应用时参考。

## UI 架构概览

```
┌─────────────────────────────────────────┐
│              CLI Mode (默认)              │
│  PTerm → 彩色输出、表格、Spinner         │
│  适合脚本化和 CI 环境                     │
├─────────────────────────────────────────┤
│              TUI Mode (--tui)            │
│  Bubble Tea → 交互式选择器、确认框        │
│  适合交互式使用和演示                      │
└─────────────────────────────────────────┘
```

## PTerm 快速参考

### 消息类型

```go
pterm.Info.Println("信息消息")       // 蓝色前缀
pterm.Success.Println("成功消息")    // 绿色前缀
pterm.Warning.Println("警告消息")    // 黄色前缀
pterm.Error.Println("错误消息")      // 红色前缀
pterm.Println("普通文本")            // 无前缀
```

### 表格

```go
// 简单表格
pterm.DefaultTable.WithHasHeader().WithData(pterm.TableData{
    {"#", "Name", "Status"},
    {"1", "task-a", "Done"},
    {"2", "task-b", "Pending"},
}).Render()

// 动态数据
tableData := pterm.TableData{{"#", "Name"}}
for i, item := range items {
    tableData = append(tableData, []string{fmt.Sprintf("%d", i+1), item})
}
pterm.DefaultTable.WithHasHeader().WithData(tableData).Render()
```

### 进度展示

```go
// Spinner
spinner, _ := pterm.DefaultSpinner.Start("Loading...")
time.Sleep(1 * time.Second)
spinner.Success("Loaded!")

// 带错误
spinner, _ := pterm.DefaultSpinner.Start("Processing...")
err := doSomething()
if err != nil {
    spinner.Fail("Failed: " + err.Error())
} else {
    spinner.Success("Done!")
}
```

### 分段和列表

```go
// 分段标题
pterm.DefaultSection.Println("Section Title")

// Bullet List
pterm.DefaultBulletList.WithItems([]pterm.BulletListItem{
    {Level: 0, Text: "First item"},
    {Level: 1, Text: "Nested item"}, // 缩进一级
    {Level: 0, Text: "Second item"},
}).Render()

// Header（全宽）
pterm.DefaultHeader.WithFullWidth().Println("Big Title")
```

### 交互确认（PTerm）

```go
// PTerm 自带的确认对话框
result, _ := pterm.DefaultInteractiveConfirm.Show("Continue?")
if result {
    pterm.Success.Println("Continuing...")
} else {
    pterm.Info.Println("Cancelled.")
}
```

## Bubble Tea 交互模式

### 选择器组件

选择器是最常用的交互组件，支持上下键导航和搜索。

**使用方式：**

```go
selected, err := tui.SelectItem("Select a task:", []string{"task-a", "task-b", "task-c"})
if err != nil {
    // 用户按了 q 或 ctrl+c
    pterm.Info.Println("Cancelled.")
    return nil
}
pterm.Success.Printf("Selected: %s\n", selected)
```

**组件实现要点：**

1. 实现 `tea.Model` 接口（`Init`, `Update`, `View`）
2. `Update` 处理键盘事件：`up/k` 上移，`down/j` 下移，`enter/space` 选择，`ctrl+c/q` 退出
3. `View` 渲染当前状态，高亮选中项
4. 通过 `tea.NewProgram(model).Run()` 启动

### 确认组件

```go
confirmed, err := tui.Confirm("Delete this item?")
if err != nil || !confirmed {
    pterm.Info.Println("Cancelled.")
    return nil
}
```

## UI 封装模式

推荐封装一个 `UI` 结构体，统一管理 TUI/CLI 模式：

```go
// internal/tui/ui.go
package tui

import "github.com/pterm/pterm"

type UI struct {
    useTUI bool
}

func New(useTUI bool) *UI {
    return &UI{useTUI: useTUI}
}

func (u *UI) Spinner(message string, action func() error) error {
    if u.useTUI {
        spinner, _ := pterm.DefaultSpinner.Start(message)
        err := action()
        if err != nil {
            spinner.Fail(message + ": " + err.Error())
            return err
        }
        spinner.Success(message)
        return nil
    }
    pterm.Println(message + "...")
    return action()
}

func (u *UI) Confirm(message string) bool {
    if u.useTUI {
        result, _ := pterm.DefaultInteractiveConfirm.Show(message)
        return result
    }
    fmt.Printf("%s [y/N]: ", message)
    var response string
    fmt.Scanln(&response)
    return response == "y" || response == "Y"
}
```

## 命令中集成 TUI 的标准模式

```go
var useTUI bool

var myCmd = &cobra.Command{
    Use:   "my-command",
    Short: "Do something",
    RunE: func(cmd *cobra.Command, args []string) error {
        if useTUI {
            return runTUI(args)
        }
        return runCLI(args)
    },
}

func init() {
    myCmd.Flags().BoolVar(&useTUI, "tui", false, "Enable interactive TUI mode")
}

func runCLI(args []string) error {
    // 直接使用 PTerm 输出
    pterm.Info.Println("Processing...")
    return nil
}

func runTUI(args []string) error {
    // 使用 Bubble Tea 交互组件
    items := []string{"option1", "option2"}
    selected, err := tui.SelectItem("Choose:", items)
    if err != nil {
        pterm.Info.Println("Cancelled.")
        return nil
    }
    pterm.Success.Printf("Selected: %s\n", selected)
    return nil
}
```

## 设计原则

1. **默认 CLI，可选 TUI**：所有命令必须支持无 `--tui` 的 CLI 模式
2. **脚本友好**：CLI 模式不使用交互式组件，适合管道和脚本
3. **一致性**：所有交互选择器使用相同的键盘快捷键（j/k/Enter/q）
4. **优雅退出**：用户取消时打印 "Cancelled" 而非返回错误
5. **PTerm 用于输出，Bubble Tea 用于交互**：不混用
