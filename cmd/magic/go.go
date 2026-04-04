package magic

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var goProxies = map[string]string{
	"default":   "https://proxy.golang.org,direct",
	"aliyun":    "https://mirrors.aliyun.com/goproxy/,direct",
	"tsinghua":  "https://mirrors.tuna.tsinghua.edu.cn/goproxy/,direct",
	"goproxy":   "https://goproxy.cn,direct",
	"ustc":      "https://goproxy.ustc.edu.cn,direct",
	"nju":       "https://goproxy.njuer.org,direct",
}

var goCmd = &cobra.Command{
	Use:   "go",
	Short: "Manage Go module proxy settings",
	Long: `Switch between different Go module proxy sources.

Supported proxies:
  - default:   Go Official (https://proxy.golang.org,direct)
  - aliyun:    Alibaba Cloud (https://mirrors.aliyun.com/goproxy/,direct)
  - tsinghua:  Tsinghua University (https://mirrors.tuna.tsinghua.edu.cn/goproxy/,direct)
  - goproxy:   Goproxy China (https://goproxy.cn,direct)
  - ustc:      USTC (https://goproxy.ustc.edu.cn,direct)
  - nju:       Nanjing University (https://goproxy.njuer.org,direct)

Examples:
  spark magic go list               # List all available proxies
  spark magic go use goproxy        # Switch to Goproxy China
  spark magic go use default        # Switch back to official proxy
  spark magic go current            # Show current proxy settings`,
}

var goListCmd = &cobra.Command{
	Use:   "list",
	Short: "List all available Go module proxies",
	RunE: func(cmd *cobra.Command, args []string) error {
		pterm.Info.Println("Available Go module proxies:")
		pterm.Println()

		for name, url := range goProxies {
			pterm.Printf("  %s: %s\n", pterm.Green(name), url)
		}
		return nil
	},
}

var goUseCmd = &cobra.Command{
	Use:   "use <proxy-name>",
	Short: "Switch to specified Go module proxy",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		proxyName := args[0]
		url, ok := goProxies[proxyName]
		if !ok {
			return fmt.Errorf("unknown proxy: %s. Run 'spark magic go list' to see available proxies", proxyName)
		}

		return setGoProxy(proxyName, url)
	},
}

var goCurrentCmd = &cobra.Command{
	Use:   "current",
	Short: "Show current Go proxy configuration",
	RunE: func(cmd *cobra.Command, args []string) error {
		return showCurrentGoProxy()
	},
}

func setGoProxy(name, url string) error {
	goBin := "go"
	if runtime.GOOS == "windows" {
		goBin = "go.exe"
	}

	cmd := exec.Command(goBin, "env", "-w", fmt.Sprintf("GOPROXY=%s", url))
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to set Go proxy: %w", err)
	}

	pterm.Success.Printf("Switched to %s Go proxy: %s\n", name, url)

	if name == "default" {
		pterm.Info.Println("Reverted to official Go proxy.")
	}

	return nil
}

func showCurrentGoProxy() error {
	goBin := "go"
	if runtime.GOOS == "windows" {
		goBin = "go.exe"
	}

	cmd := exec.Command(goBin, "env", "GOPROXY")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to get Go proxy config: %w", err)
	}

	proxy := string(output)
	if len(proxy) > 0 && proxy[len(proxy)-1] == '\n' {
		proxy = proxy[:len(proxy)-1]
	}

	pterm.Info.Printf("Current GOPROXY: %s\n", proxy)

	for name, url := range goProxies {
		if proxy == url {
			pterm.Success.Printf("Using %s mirror\n", name)
			return nil
		}
	}

	if proxy == "" || proxy == "https://proxy.golang.org,direct" {
		pterm.Info.Println("Using default Go proxy")
	} else {
		pterm.Warning.Println("Using custom proxy")
	}

	return nil
}

func init() {
	goCmd.AddCommand(goListCmd)
	goCmd.AddCommand(goUseCmd)
	goCmd.AddCommand(goCurrentCmd)
	MagicCmd.AddCommand(goCmd)
}
