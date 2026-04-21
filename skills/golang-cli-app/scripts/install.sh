#!/usr/bin/env bash
# Golang CLI App Skill Installer (macOS / Linux)
# Usage: ./install.sh [--system | --project] [--agent <name>]
#
# Options:
#   --system        Install to system skill directories (default: ~/.config/agents/skills/)
#   --project       Install to current project directory (./.agents/skills/)
#   --agent <name>  Target specific agent (claude-code, kimi, codex, opencode)
#   -h, --help      Show this help message
#
# Examples:
#   ./install.sh --system                     # Install to all system agent dirs
#   ./install.sh --system --agent kimi        # Install to kimi system dir only
#   ./install.sh --project                    # Install to current project

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_NAME="$(basename "$SKILL_ROOT")"
INSTALL_MODE=""
TARGET_AGENT=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

usage() {
    sed -n '/^# Golang CLI App Skill Installer/,/^# Examples:/p' "$0" | sed 's/^# //'
    echo ""
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --system)
                INSTALL_MODE="system"
                shift
                ;;
            --project)
                INSTALL_MODE="project"
                shift
                ;;
            --agent)
                TARGET_AGENT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                echo -e "${RED}Error: Unknown option $1${NC}" >&2
                usage
                exit 1
                ;;
            *)
                echo -e "${RED}Error: Unknown argument $1${NC}" >&2
                usage
                exit 1
                ;;
        esac
    done
}

check_go() {
    if command -v go &>/dev/null; then
        local version
        version="$(go version)"
        echo -e "${GREEN}[OK]${NC} Go found: $version"
        return 0
    else
        echo -e "${YELLOW}[WARN]${NC} Go is not installed."
        return 1
    fi
}

check_cobra() {
    if command -v cobra &>/dev/null; then
        echo -e "${GREEN}[OK]${NC} Cobra CLI generator found"
        return 0
    else
        echo -e "${YELLOW}[INFO]${NC} Cobra CLI generator not installed (optional, for scaffolding)"
        return 1
    fi
}

get_system_target_dirs() {
    local dirs=()
    case "$TARGET_AGENT" in
        "")
            dirs+=("$HOME/.config/agents/skills")
            dirs+=("$HOME/.claude/skills")
            dirs+=("$HOME/.kimi/skills")
            dirs+=("$HOME/.codex/skills")
            dirs+=("$HOME/.opencode/skills")
            ;;
        claude-code)
            dirs+=("$HOME/.claude/skills")
            ;;
        kimi)
            dirs+=("$HOME/.kimi/skills")
            dirs+=("$HOME/.config/agents/skills")
            ;;
        codex)
            dirs+=("$HOME/.codex/skills")
            ;;
        opencode)
            dirs+=("$HOME/.opencode/skills")
            ;;
        *)
            echo -e "${RED}Error: Unknown agent '$TARGET_AGENT'${NC}" >&2
            echo "Supported agents: claude-code, kimi, codex, opencode" >&2
            exit 1
            ;;
    esac
    echo "${dirs[@]}"
}

get_project_target_dirs() {
    local dirs=()
    dirs+=("./.agents/skills")
    dirs+=("./.kimi/skills")
    dirs+=("./.claude/skills")
    echo "${dirs[@]}"
}

install_skill_to_dir() {
    local target_dir="$1"
    local link_path="$target_dir/$SKILL_NAME"

    mkdir -p "$target_dir"

    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        echo -e "${YELLOW}  [SKIP]${NC} $SKILL_NAME already exists at $link_path"
        return 1
    fi

    ln -s "$SKILL_ROOT" "$link_path"
    echo -e "${GREEN}  [OK]${NC}   $SKILL_NAME -> $link_path"
    return 0
}

install_system() {
    echo -e "${BLUE}Installing $SKILL_NAME to system directories...${NC}"
    local target_dirs=($(get_system_target_dirs))
    local installed=0
    local skipped=0

    for target_dir in "${target_dirs[@]}"; do
        if install_skill_to_dir "$target_dir"; then
            ((installed++)) || true
        else
            ((skipped++)) || true
        fi
    done

    echo ""
    echo -e "${GREEN}System installation complete.${NC}"
    echo "  Installed: $installed"
    echo "  Skipped: $skipped"
}

install_project() {
    echo -e "${BLUE}Installing $SKILL_NAME to project directories...${NC}"

    local target_dirs=($(get_project_target_dirs))
    local installed=0
    local skipped=0

    for target_dir in "${target_dirs[@]}"; do
        if install_skill_to_dir "$target_dir"; then
            ((installed++)) || true
        else
            ((skipped++)) || true
        fi
    done

    echo ""
    echo -e "${GREEN}Project installation complete.${NC}"
    echo "  Installed: $installed"
    echo "  Skipped: $skipped"
}

main() {
    parse_args "$@"

    if [ -z "$INSTALL_MODE" ]; then
        echo -e "${RED}Error: Must specify --system or --project${NC}" >&2
        usage
        exit 1
    fi

    echo -e "${BLUE}Golang CLI App Skill Installer${NC}"
    echo ""

    check_go
    check_cobra

    echo ""
    case "$INSTALL_MODE" in
        system)
            install_system
            ;;
        project)
            install_project
            ;;
    esac

    echo ""
    echo "Skill installed: $SKILL_NAME"
    echo ""
    echo "The skill provides code examples and best practices for building Go CLI apps."
    echo "Agents will reference this skill when helping you create CLI applications."
}

main "$@"
