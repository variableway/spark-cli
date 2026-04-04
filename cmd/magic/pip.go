package magic

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var pipSources = map[string]string{
	"default":    "https://pypi.org/simple",
	"tsinghua":   "https://pypi.tuna.tsinghua.edu.cn/simple",
	"aliyun":     "https://mirrors.aliyun.com/pypi/simple",
	"douban":     "https://pypi.doubanio.com/simple",
	"ustc":       "https://pypi.mirrors.ustc.edu.cn/simple",
	"tencent":    "https://mirrors.cloud.tencent.com/pypi/simple",
}

var pipCmd = &cobra.Command{
	Use:   "pip",
	Short: "Manage Python pip mirror sources",
	Long: `Switch between different Python pip mirror sources.

Supported sources:
  - default:   PyPI Official (https://pypi.org/simple)
  - tsinghua:  Tsinghua University (https://pypi.tuna.tsinghua.edu.cn/simple)
  - aliyun:    Alibaba Cloud (https://mirrors.aliyun.com/pypi/simple)
  - douban:    Douban (https://pypi.doubanio.com/simple)
  - ustc:      USTC (https://pypi.mirrors.ustc.edu.cn/simple)
  - tencent:   Tencent Cloud (https://mirrors.cloud.tencent.com/pypi/simple)

Examples:
  spark magic pip list              # List all available sources
  spark magic pip use tsinghua      # Switch to Tsinghua mirror
  spark magic pip use default       # Switch back to official PyPI
  spark magic pip current           # Show current source`,
}

var pipListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all available pip sources",
	RunE: func(cmd *cobra.Command, args []string) error {
		pterm.Info.Println("Available pip sources:")
		pterm.Println()

		for name, url := range pipSources {
			pterm.Printf("  %s: %s\n", pterm.Green(name), url)
		}
		return nil
	},
}

var pipUseCmd = &cobra.Command{
	Use:   "use <source-name>",
	Short: "Switch to specified pip source",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		sourceName := args[0]
		url, ok := pipSources[sourceName]
		if !ok {
			return fmt.Errorf("unknown source: %s. Run 'spark magic pip list' to see available sources", sourceName)
		}

		return setPipSource(sourceName, url)
	},
}

var pipCurrentCmd = &cobra.Command{
	Use:   "current",
	Short: "Show current pip source configuration",
	RunE: func(cmd *cobra.Command, args []string) error {
		return showCurrentPipSource()
	},
}

func getPipConfigFile() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".pip", "pip.conf")
}

func setPipSource(name, url string) error {
	pipDir := filepath.Dir(getPipConfigFile())
	if err := os.MkdirAll(pipDir, 0755); err != nil {
		return fmt.Errorf("failed to create pip config directory: %w", err)
	}

	configContent := fmt.Sprintf(`[global]
index-url = %s
trusted-host = %s
`, url, extractHost(url))

	if err := os.WriteFile(getPipConfigFile(), []byte(configContent), 0644); err != nil {
		return fmt.Errorf("failed to write pip config: %w", err)
	}

	pterm.Success.Printf("Switched to %s mirror: %s\n", name, url)
	pterm.Info.Printf("Config file: %s\n", getPipConfigFile())

	if name == "default" {
		pterm.Info.Println("You can now remove the config to use default:")
		pterm.Printf("  rm %s\n", getPipConfigFile())
	}

	return nil
}

func showCurrentPipSource() error {
	configFile := getPipConfigFile()

	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		pterm.Info.Println("No custom pip source configured.")
		pterm.Info.Println("Using default: https://pypi.org/simple")
		return nil
	}

	content, err := os.ReadFile(configFile)
	if err != nil {
		return fmt.Errorf("failed to read pip config: %w", err)
	}

	pterm.Info.Println("Current pip configuration:")
	pterm.Println()
	pterm.Println(string(content))

	cmd := exec.Command("pip", "config", "get", "global.index-url")
	output, err := cmd.Output()
	if err == nil {
		pterm.Info.Printf("Active index-url: %s", string(output))
	}

	return nil
}

func extractHost(url string) string {
	url = strings.TrimPrefix(url, "https://")
	url = strings.TrimPrefix(url, "http://")
	if idx := strings.Index(url, "/"); idx != -1 {
		url = url[:idx]
	}
	return url
}

func init() {
	pipCmd.AddCommand(pipListCmd)
	pipCmd.AddCommand(pipUseCmd)
	pipCmd.AddCommand(pipCurrentCmd)
	MagicCmd.AddCommand(pipCmd)
}
