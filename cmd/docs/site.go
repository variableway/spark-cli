package docs

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/pterm/pterm"
	"github.com/spf13/cobra"
)

var siteCmd = &cobra.Command{
	Use:   "site",
	Short: "Initialize docmd site configuration",
	Long: `Initialize docmd documentation site configuration.

Creates docmd.config.js using the docs/ directory as source.
Auto-detects project title and URL from git remote.
Installs @docmd/core if not found.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		root, err := cmd.Flags().GetString("root")
		if err != nil {
			return err
		}
		return initSite(root)
	},
}

func initSite(root string) error {
	absRoot, err := filepath.Abs(root)
	if err != nil {
		return err
	}

	title, siteURL := detectRepoInfo(absRoot)

	pterm.Info.Printf("Project title: %s\n", title)
	pterm.Info.Printf("Site URL: %s\n", siteURL)

	if err := ensureDocmdInstalled(); err != nil {
		return err
	}

	configPath := filepath.Join(absRoot, "docmd.config.js")
	if _, err := os.Stat(configPath); err == nil {
		overwrite, _ := pterm.DefaultInteractiveConfirm.Show(
			fmt.Sprintf("docmd.config.js already exists. Overwrite?"),
		)
		if !overwrite {
			pterm.Info.Println("Skipped.")
			return nil
		}
	}

	config := generateConfig(title, siteURL)
	if err := os.WriteFile(configPath, []byte(config), 0644); err != nil {
		return fmt.Errorf("failed to write docmd.config.js: %w", err)
	}
	pterm.Success.Println("Created docmd.config.js")

	packageJSON := filepath.Join(absRoot, "package.json")
	if _, err := os.Stat(packageJSON); os.IsNotExist(err) {
		if err := initPackageJSON(absRoot); err != nil {
			return err
		}
	}

	if err := runNpmInstall(absRoot); err != nil {
		return err
	}

	pterm.Success.Println("Docmd site initialized. Run `docmd dev` to preview.")
	return nil
}

func detectRepoInfo(root string) (title, siteURL string) {
	title = filepath.Base(root)
	siteURL = ""

	cmd := exec.Command("git", "remote", "get-url", "origin")
	cmd.Dir = root
	remoteURL, err := cmd.Output()
	if err != nil {
		return
	}
	url := strings.TrimSpace(string(remoteURL))

	owner, repo := parseGitURL(url)
	if owner != "" && repo != "" {
		title = repo
		siteURL = fmt.Sprintf("https://%s.github.io/%s", owner, repo)
	}
	return
}

func parseGitURL(raw string) (owner, repo string) {
	url := raw
	url = strings.TrimPrefix(url, "git@github.com:")
	url = strings.TrimPrefix(url, "https://github.com/")
	url = strings.TrimPrefix(url, "ssh://git@github.com/")
	url = strings.TrimSuffix(url, ".git")

	parts := strings.SplitN(url, "/", 2)
	if len(parts) == 2 {
		owner = parts[0]
		repo = parts[1]
	}
	return
}

func ensureDocmdInstalled() error {
	if _, err := exec.LookPath("docmd"); err == nil {
		return nil
	}

	pterm.Info.Println("docmd not found. Installing @docmd/core globally...")
	cmd := exec.Command("npm", "install", "-g", "@docmd/core")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to install docmd: %w", err)
	}
	pterm.Success.Println("Installed @docmd/core globally.")
	return nil
}

func generateConfig(title, siteURL string) string {
	return fmt.Sprintf(`// docmd.config.js
export default defineConfig({
  title: '%s',
  url: '%s',

  src: 'docs',
  out: 'site',

  layout: {
    spa: true,
    header: { enabled: true },
    sidebar: { collapsible: true, defaultCollapsed: false },
    optionsMenu: {
      position: 'sidebar-top',
      components: { search: true, themeSwitch: true, sponsor: null },
    },
    footer: {
      style: 'minimal',
      content: '© ' + new Date().getFullYear() + ' %s',
      branding: true,
    },
  },

  theme: {
    name: 'sky',
    appearance: 'system',
    codeHighlight: true,
    customCss: [],
  },

  minify: true,
  autoTitleFromH1: true,
  copyCode: true,
  pageNavigation: true,

  navigation: [
    { title: 'Home', path: '/', icon: 'home' },
  ],

  plugins: {
    seo: {
      defaultDescription: '%s documentation',
      openGraph: { defaultImage: '' },
      twitter: { cardType: 'summary_large_image' },
    },
    sitemap: { defaultChangefreq: 'weekly' },
    search: {},
    mermaid: {},
    llms: { fullContext: true },
  },
});
`, title, siteURL, title, title)
}

func initPackageJSON(root string) error {
	cmd := exec.Command("npm", "init", "-y")
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to init package.json: %w", err)
	}
	pterm.Success.Println("Created package.json")
	return nil
}

func runNpmInstall(root string) error {
	cmd := exec.Command("npm", "install")
	cmd.Dir = root
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to run npm install: %w", err)
	}
	pterm.Success.Println("Dependencies installed.")
	return nil
}

func init() {
	siteCmd.Flags().String("root", ".", "Project root directory")
	DocsCmd.AddCommand(siteCmd)
}
