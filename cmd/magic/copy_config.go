package magic

import (
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strings"

	"spark/internal/templates"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var copyConfigCmd = &cobra.Command{
	Use:   "copy-config [<user@host:path>]",
	Short: "Deploy bundled Neovim & Ghostty config templates to a PC",
	Long: `Deploy the built-in nvim and Ghostty config templates to the default
locations (~/.config/nvim/ and ~/.config/ghostty/), or to a custom target.

Without arguments, templates are written directly to the default config paths
on the current machine. With a target argument, they deploy to that path or
SSH remote.

The templates are embedded into the Spark binary at build time and serve as
a reference starting point. Customize them in internal/templates/dotfiles/
before building, then deploy with this command.

Uses rsync (preferred) for transfer. Falls back to cp for local targets.

Examples:
  spark magic copy-config                       # deploy to ~/.config/ on this machine
  spark magic copy-config user@192.168.1.100:~/ # deploy to a remote PC
  spark magic copy-config /mnt/usb/backup/      # deploy to a custom local path`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) == 0 {
			return deployDefaults()
		}
		return deployToTarget(args[0])
	},
}

// deployDefaults deploys templates directly to the default config paths.
func deployDefaults() error {
	home, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("cannot determine home directory: %w", err)
	}

	tmpDir, err := os.MkdirTemp("", "spark-dotfiles-*")
	if err != nil {
		return fmt.Errorf("failed to create temp directory: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	if err := extractTemplates(tmpDir); err != nil {
		return fmt.Errorf("failed to extract templates: %w", err)
	}

	srcDir := filepath.Join(tmpDir, "dotfiles")

	pterm.Info.Println("Deploying config templates to default locations:")
	pterm.Printf("  • nvim    → %s\n", pterm.Cyan(filepath.Join(home, ".config", "nvim")))
	pterm.Printf("  • ghostty → %s\n", pterm.Cyan(filepath.Join(home, ".config", "ghostty")))
	pterm.Println()

	nvimDest := filepath.Join(home, ".config", "nvim")
	ghosttyDest := filepath.Join(home, ".config", "ghostty")

	if _, err := exec.LookPath("rsync"); err == nil {
		if err := rsyncDir(filepath.Join(srcDir, "nvim")+"/", nvimDest); err != nil {
			return fmt.Errorf("deploying nvim: %w", err)
		}
		if err := rsyncDir(filepath.Join(srcDir, "ghostty")+"/", ghosttyDest); err != nil {
			return fmt.Errorf("deploying ghostty: %w", err)
		}
	} else {
		pterm.Warning.Println("rsync not found, falling back to cp")
		if err := cpDir(filepath.Join(srcDir, "nvim"), nvimDest); err != nil {
			return fmt.Errorf("deploying nvim: %w", err)
		}
		if err := cpDir(filepath.Join(srcDir, "ghostty"), ghosttyDest); err != nil {
			return fmt.Errorf("deploying ghostty: %w", err)
		}
	}

	pterm.Success.Println("Config templates deployed to default locations!")
	return nil
}

// deployToTarget extracts the embedded templates to a temp dir then copies to target.
func deployToTarget(target string) error {
	tmpDir, err := os.MkdirTemp("", "spark-dotfiles-*")
	if err != nil {
		return fmt.Errorf("failed to create temp directory: %w", err)
	}
	defer os.RemoveAll(tmpDir)

	if err := extractTemplates(tmpDir); err != nil {
		return fmt.Errorf("failed to extract templates: %w", err)
	}

	pterm.Info.Println("Deploying bundled config templates:")
	pterm.Println("  • nvim")
	pterm.Println("  • ghostty")
	pterm.Println()

	srcDir := filepath.Join(tmpDir, "dotfiles")
	if isRemoteTarget(target) {
		return deployRemote(srcDir, target)
	}
	return deployLocal(srcDir, target)
}

// extractTemplates writes all embedded dotfiles under destDir.
func extractTemplates(destDir string) error {
	efs := templates.Dotfiles
	root := "dotfiles"

	return fs.WalkDir(efs, root, func(fpath string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		// Reconstruct destination path (strip the "dotfiles" prefix)
		rel, _ := filepath.Rel(root, fpath)
		target := filepath.Join(destDir, root, rel)

		if d.IsDir() {
			return os.MkdirAll(target, 0755)
		}

		// Write file
		data, err := efs.ReadFile(fpath)
		if err != nil {
			return fmt.Errorf("reading embedded %s: %w", fpath, err)
		}
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		//nolint:gosec // embedded templates are safe
		return os.WriteFile(target, data, 0644)
	})
}

// isRemoteTarget detects SSH-style targets like user@host:path
func isRemoteTarget(target string) bool {
	return strings.Contains(target, "@") || strings.Contains(target, ":/")
}

func deployLocal(srcDir, dest string) error {
	dest = path.Clean(dest)
	if _, err := exec.LookPath("rsync"); err == nil {
		return rsyncDir(srcDir+"/", dest)
	}

	pterm.Warning.Println("rsync not found, falling back to cp")
	return cpDir(srcDir, dest)
}

func deployRemote(srcDir, target string) error {
	if _, err := exec.LookPath("rsync"); err != nil {
		return fmt.Errorf("rsync is required for remote copy but not found in PATH")
	}
	return rsyncDir(srcDir+"/", target)
}

func rsyncDir(src, dest string) error {
	pterm.Info.Println("Syncing templates via rsync...")

	cmd := exec.Command("rsync", "-avz", "--progress", src, dest)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("rsync failed: %w", err)
	}

	pterm.Success.Println("Templates deployed successfully!")
	return nil
}

func cpDir(src, dest string) error {
	pterm.Info.Println("Copying templates...")

	if err := os.MkdirAll(dest, 0755); err != nil {
		return fmt.Errorf("failed to create destination %s: %w", dest, err)
	}

	cmd := exec.Command("cp", "-r", src, dest)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("copy failed: %w", err)
	}

	pterm.Success.Println("Templates deployed successfully!")
	return nil
}

func init() {
	MagicCmd.AddCommand(copyConfigCmd)
}
