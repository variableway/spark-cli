package git

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"

	"github.com/spf13/cobra"
)

var cloneCmd = &cobra.Command{
	Use:   "clone <url-or-slug> [directory] [-- <git-args>]",
	Short: "Clone a GitHub repository using gh repo clone (defaults to SSH)",
	Long: `Clone a GitHub repository using the GitHub CLI ('gh repo clone').

This command converts various GitHub URL formats into the owner/repo slug
and invokes 'gh repo clone', which defaults to SSH for better stability
in regions where HTTPS connections to GitHub are unreliable.

Supported inputs:
  - https://github.com/owner/repo.git
  - git@github.com:owner/repo.git
  - github.com/owner/repo
  - owner/repo

Extra arguments after '--' are forwarded to 'git clone'.`,
	Example: `  spark git clone https://github.com/Nutlope/pdf-to-interactive-lesson.git
  spark git clone Nutlope/pdf-to-interactive-lesson
  spark git clone https://github.com/owner/repo.git my-dir -- --branch main --depth 1`,
	Args: cobra.MinimumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]

		slug, err := parseRepoSlug(input)
		if err != nil {
			return err
		}

		cmdPath := cmd.CommandPath()
		cmdArgs := resolveCmdArgs(cmdPath)

		var dir string
		var gitArgs []string
		if len(cmdArgs) > 1 {
			sepIdx := -1
			for i, a := range cmdArgs[1:] {
				if a == "--" {
					sepIdx = i + 1
					break
				}
			}
			if sepIdx == -1 {
				dir = cmdArgs[1]
			} else {
				if sepIdx > 1 {
					dir = cmdArgs[1]
				}
				if sepIdx+1 < len(cmdArgs) {
					gitArgs = cmdArgs[sepIdx+1:]
				}
			}
		}

		ghArgs := []string{"repo", "clone", slug}
		if dir != "" {
			ghArgs = append(ghArgs, dir)
		}
		if len(gitArgs) > 0 {
			ghArgs = append(ghArgs, "--")
			ghArgs = append(ghArgs, gitArgs...)
		}

		fmt.Printf("Cloning %s via gh (SSH)...\n", slug)
		c := exec.Command("gh", ghArgs...)
		c.Stdout = os.Stdout
		c.Stderr = os.Stderr
		c.Stdin = os.Stdin
		return c.Run()
	},
}

func resolveCmdArgs(cmdPath string) []string {
	parts := strings.Fields(cmdPath)
	if len(parts) == 0 {
		return os.Args[1:]
	}
	if len(os.Args) <= len(parts) {
		return nil
	}
	return os.Args[len(parts):]
}

var repoSlugRegex = regexp.MustCompile(`^(?:https?://(?:www\.)?github\.com/|git@github\.com:|(?:www\.)?github\.com/)?([^/]+/[^/]+?)(?:\.git)?/?$`)

func parseRepoSlug(input string) (string, error) {
	input = strings.TrimSpace(input)
	input = strings.TrimSuffix(input, "/")

	matches := repoSlugRegex.FindStringSubmatch(input)
	if len(matches) == 2 {
		return matches[1], nil
	}

	return "", fmt.Errorf("unable to parse GitHub repository from %q", input)
}

func init() {
	GitCmd.AddCommand(cloneCmd)
}
