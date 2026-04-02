# Spark Skills 仓库构建过程

本文档记录了从 0 到 1 构建 `spark-skills` 仓库的全过程，用于后续回顾和持续迭代。

## 背景与动机

之前有一个独立的 `github-task-workflow` skill，放在 `spark-cli` 项目内部。随着使用场景扩展，需要：

1. 把 skill 从业务项目中剥离，形成独立的 skill 仓库
2. 建立统一的 skill 管理规范，方便后续添加更多技能
3. 让 skill 能同时被多个 AI Agent（Claude Code、Kimi、Codex、OpenCode）识别和使用

## 目标

- 新建目录 `spark-skills`
- 迁移并保留 `github-task-workflow` 的完整功能
- 设计多 Agent 兼容的目录结构和安装机制
- 把构建过程文档化，写入仓库本身

## 结构设计

### 1. 单 Skill 结构

参考 Claude Code 和 Kimi CLI 的 skill 规范，采用以下最小结构：

```
<skill-name>/
├── SKILL.md              # 唯一入口，必须包含标准 frontmatter
├── scripts/              # 可执行脚本（可选）
└── references/           # 扩展参考文档（可选）
```

这样每个 skill 都是自包含的，任何 Agent 读取 `SKILL.md` 即可理解该 skill 的用途和用法。

### 2. 仓库级结构

```
spark-skills/
├── README.md             # 仓库总览、安装说明、skill 目录
├── SETUP.md              # 本文件：构建过程记录
├── install.sh            # 一键安装脚本：将 skills 链接到各 Agent 目录
└── <skill-name>/         # 单个 skill 目录
```

## 迁移 `github-task-workflow`

### 原结构

原 skill 位于 `spark-cli/github-task-workflow/`：

```
github-task-workflow/
├── SKILL.md
├── references/workflow.md
└── scripts/
    ├── config_loader.py
    ├── create_issue.py
    └── update_issue.py
```

### 迁移步骤

1. 在 `spark-skills` 下创建同名目录
2. 直接复制 `scripts/` 和 `references/` 下的所有文件（功能已验证，无需改动）
3. 重写 `SKILL.md`：
   - 补充 `supported_agents` frontmatter
   - 增加"多 Agent 兼容"的说明段落
   - 保持原有使用示例和脚本路径不变

### 为什么不改动 Python 脚本

`github-task-workflow` 的脚本已经满足：
- 纯标准库（`urllib` + `json` + `argparse`）
- 自带配置加载分层逻辑
- 运行稳定

因此迁移时只做目录搬迁和文档增强，不做代码重构，避免引入回归。

## 多 Agent 支持方案

### 兼容层设计

不同 Agent 对 skill 的识别机制基本一致：读取目录下的 `SKILL.md`。差异主要在于：
- 安装目录不同
- 个别 Agent 可能额外读取 `.json` manifest 文件

因此采用"通用 Markdown + 安装脚本"的折中方案：

1. **通用层**：所有 skill 统一提供 `SKILL.md`，内容对各 Agent 无歧义
2. **安装层**：提供 `install.sh`，负责将 skill 目录符号链接（symlink）到对应 Agent 的 skills 目录

### 安装脚本行为

```bash
./install.sh <agent-name>
```

脚本会：
1. 检测当前系统（macOS / Linux）
2. 根据 agent-name 查找对应的技能根目录
3. 将 `spark-skills` 下的所有 skill 子目录以 symlink 形式安装到目标目录
4. 跳过已存在的链接，避免重复创建

支持的 `agent-name`：
- `claude-code` → `~/.claude/skills/`
- `kimi` → `~/.kimi/skills/`
- `codex` → `~/.codex/skills/`
- `opencode` → `~/.opencode/skills/`

> 未来如需支持 Windows，可将 `install.sh` 扩展为 `install.ps1`。

## 过程中的决策记录

### 决策 1：是否保留原 `github-task-workflow` 的独立 git 历史？

**选择**：不保留，直接在新仓库中复制文件。

**理由**：
- 原 skill 历史很短，只有几个文件
- 新仓库的目标是"从零建立个人 skill 集合"，独立历史更有价值
- 复制文件足够简单，后续迭代会产生新历史

### 决策 2：是否为每个 Agent 生成不同的 manifest 文件？

**选择**：暂不为每个 Agent 单独生成 manifest，统一使用 `SKILL.md`。

**理由**：
- Claude Code 和 Kimi CLI 均只认 `SKILL.md`
- Codex 和 OpenCode 目前也主要走 markdown 描述
- 如果未来某个 Agent 强制要求 `.json` manifest，可以在 `install.sh` 中为该 Agent 动态生成

### 决策 3：Skill 脚本是否放在 `SKILL.md` 同级还是 `scripts/` 子目录？

**选择**：保持 `scripts/` 子目录。

**理由**：
- 原结构已经如此，用户习惯该路径
- `SKILL.md` 中引用路径清晰（如 `python scripts/create_issue.py`）
- 子目录结构更整洁

## 后续计划

1. 在本地验证 `install.sh` 对 Claude Code 和 Kimi 的安装效果
2. 观察各 Agent 加载 skill 后的行为，收集反馈
3. 逐步添加新 skill，例如：
   - `daily-review`：基于对话历史生成每日回顾
   - `code-review`：自动执行代码审查清单
   - `doc-generator`：根据代码变更自动生成/更新文档
4. 如某 Agent 推出新的 skill 规范，再评估是否引入 agent-specific 的 manifest

## 时间线

- **2026-04-03**：完成 `spark-skills` 仓库初始化和 `github-task-workflow` 迁移
