package magic

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var npmRegistries = map[string]string{
	"default":    "https://registry.npmjs.org/",
	"taobao":     "https://registry.npmmirror.com/",
	"aliyun":     "https://registry.npmmirror.com/",
	"tencent":    "https://mirrors.cloud.tencent.com/npm/",
	"huawei":     "https://mirrors.huaweicloud.com/repository/npm/",
	"ustc":       "https://npmreg.mirrors.ustc.edu.cn/",
}

var nodeCmd = &cobra.Command{
	Use:   "node",
	Short: "Manage Node.js npm registry settings",
	Long: `Switch between different npm registry mirrors.

Supported registries:
  - default:   npm Official (https://registry.npmjs.org/)
  - taobao:    npmmirror (Taobao) (https://registry.npmmirror.com/)
  - aliyun:    npmmirror (Aliyun) (https://registry.npmmirror.com/)
  - tencent:   Tencent Cloud (https://mirrors.cloud.tencent.com/npm/)
  - huawei:    Huawei Cloud (https://mirrors.huaweicloud.com/repository/npm/)
  - ustc:      USTC (https://npmreg.mirrors.ustc.edu.cn/)

Examples:
  spark magic node list             # List all available registries
  spark magic node use taobao       # Switch to npmmirror (Taobao)
  spark magic node use default      # Switch back to official npm registry
  spark magic node current          # Show current registry`,
}

var nodeListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all available npm registries",
	RunE: func(cmd *cobra.Command, args []string) error {
		pterm.Info.Println("Available npm registries:")
		pterm.Println()

		for name, url := range npmRegistries {
			pterm.Printf("  %s: %s\n", pterm.Green(name), url)
		}
		return nil
	},
}

var nodeUseCmd = &cobra.Command{
	Use:   "use <registry-name>",
	Short: "Switch to specified npm registry",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		registryName := args[0]
		url, ok := npmRegistries[registryName]
		if !ok {
			return fmt.Errorf("unknown registry: %s. Run 'spark magic node list' to see available registries", registryName)
		}

		return setNpmRegistry(registryName, url)
	},
}

var nodeCurrentCmd = &cobra.Command{
	Use:   "current",
	Short: "Show current npm registry configuration",
	RunE: func(cmd *cobra.Command, args []string) error {
		return showCurrentNpmRegistry()
	},
}

func setNpmRegistry(name, url string) error {
	npmBin := "npm"

	cmd := exec.Command(npmBin, "config", "set", "registry", url)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to set npm registry: %w", err)
	}

	pterm.Success.Printf("Switched to %s npm registry: %s\n", name, url)

	if name == "default" {
		pterm.Info.Println("Reverted to official npm registry.")
	}

	return nil
}

func showCurrentNpmRegistry() error {
	npmBin := "npm"

	cmd := exec.Command(npmBin, "config", "get", "registry")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get npm registry config: %w", err)
	}

	registry := string(output)
	if len(registry) > 0 && registry[len(registry)-1] == '\n' {
		registry = registry[:len(registry)-1]
	}

	pterm.Info.Printf("Current npm registry: %s\n", registry)

	for name, url := range npmRegistries {
		if registry == url {
			pterm.Success.Printf("Using %s mirror\n", name)
			return nil
		}
	}

	if registry == "https://registry.npmjs.org/" {
		pterm.Info.Println("Using default npm registry")
	} else {
		pterm.Warning.Println("Using custom registry")
	}

	return nil
}

func init() {
	nodeCmd.AddCommand(nodeListCmd)
	nodeCmd.AddCommand(nodeUseCmd)
	nodeCmd.AddCommand(nodeCurrentCmd)
	MagicCmd.AddCommand(nodeCmd)
}
