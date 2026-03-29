package magic

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var flushDNSCmd = &cobra.Command{
	Use:   "flush-dns",
	Short: "Flush DNS cache on the current system",
	Long: `Flush the DNS cache on macOS, Windows, or Linux.

This command automatically detects the operating system and
runs the appropriate command to clear the DNS cache.

Examples:
  spark magic flush-dns

Platform-specific commands used:
  - macOS:   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
  - Windows: ipconfig /flushdns
  - Linux:   sudo systemctl restart systemd-resolved (or appropriate service)`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return flushDNS()
	},
}

func flushDNS() error {
	osName := runtime.GOOS

	pterm.Info.Printf("Detected OS: %s\n", osName)
	pterm.Println()

	switch osName {
	case "darwin":
		return flushDNSMac()
	case "windows":
		return flushDNSWindows()
	case "linux":
		return flushDNSLinux()
	default:
		return fmt.Errorf("unsupported operating system: %s", osName)
	}
}

func flushDNSMac() error {
	pterm.Info.Println("Flushing DNS cache on macOS...")

	commands := [][]string{
		{"sudo", "dscacheutil", "-flushcache"},
		{"sudo", "killall", "-HUP", "mDNSResponder"},
	}

	for _, cmdArgs := range commands {
		cmd := exec.Command(cmdArgs[0], cmdArgs[1:]...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin

		if err := cmd.Run(); err != nil {
			pterm.Warning.Printf("Command failed: %v\n", err)
		}
	}

	pterm.Success.Println("DNS cache flushed successfully on macOS!")
	return nil
}

func flushDNSWindows() error {
	pterm.Info.Println("Flushing DNS cache on Windows...")

	cmd := exec.Command("ipconfig", "/flushdns")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to flush DNS cache: %w", err)
	}

	pterm.Success.Println("DNS cache flushed successfully on Windows!")
	return nil
}

func flushDNSLinux() error {
	pterm.Info.Println("Flushing DNS cache on Linux...")

	flushMethods := [][]string{
		{"sudo", "systemctl", "restart", "systemd-resolved"},
		{"sudo", "service", "nscd", "restart"},
		{"sudo", "service", "dnsmasq", "restart"},
		{"sudo", "rndc", "flush"},
	}

	var lastErr error
	for _, cmdArgs := range flushMethods {
		cmd := exec.Command(cmdArgs[0], cmdArgs[1:]...)
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		cmd.Stdin = os.Stdin

		if err := cmd.Run(); err != nil {
			lastErr = err
			continue
		}

		pterm.Success.Println("DNS cache flushed successfully on Linux!")
		return nil
	}

	if lastErr != nil {
		pterm.Warning.Println("Some methods failed, but DNS cache may still be flushed.")
		pterm.Info.Println("You may need to restart your network manager or reboot.")
	}

	return nil
}

func init() {
	MagicCmd.AddCommand(flushDNSCmd)
}
