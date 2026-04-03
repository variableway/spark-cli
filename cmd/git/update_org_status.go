package git

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"spark/internal/github"

	"github.com/spf13/cobra"
)

var (
	updateOrgStatusOutput        string
	updateOrgStatusDryRun        bool
	updateOrgStatusUpdateDotGitHub bool
	updateOrgStatusSection       string
	updateOrgStatusSkipPush      bool
)

var updateOrgStatusCmd = &cobra.Command{
	Use:   "update-org-status <org-name-or-url>",
	Short: "Update organization repositories status to README.md",
	Long: `Fetch all repositories from a GitHub organization, sort by stars,
and update README.md file with a project list table.

By default, updates the local .github/README.md file.
Use --update-dot-github to update the organization's .github repository directly.

This command will:
1. Fetch all public repositories from the specified organization
2. Sort repositories by stargazers count (descending)
3. Update README.md (local or .github repo) with a "Project List" section
4. Commit and push changes (unless --skip-push is used)`,
	Args: cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		input := args[0]

		orgName, err := github.ParseOrgFromURL(input)
		if err != nil {
			return err
		}

		fmt.Printf("Fetching repositories for organization: %s\n", orgName)

		repos, err := github.GetOrgRepos(orgName)
		if err != nil {
			return err
		}

		fmt.Printf("Found %d repositories\n", len(repos))

		// Sort by stargazers count (descending)
		sort.Slice(repos, func(i, j int) bool {
			return repos[i].Stargazers > repos[j].Stargazers
		})

		// Generate project list section content
		sectionContent := generateProjectListSection(orgName, repos)

		if updateOrgStatusDryRun {
			fmt.Printf("\n--- Dry Run: Content to be inserted ---\n")
			fmt.Println(sectionContent)
			return nil
		}

		// Determine target path and update strategy
		if updateOrgStatusUpdateDotGitHub {
			return updateDotGitHubRepo(orgName, sectionContent)
		}

		return updateLocalFile(orgName, sectionContent)
	},
}

func generateProjectListSection(orgName string, repos []github.Repository) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("## %s\n\n", updateOrgStatusSection))

	// Add timestamp
	sb.WriteString(fmt.Sprintf("*Last updated: %s*\n\n", time.Now().Format("2006-01-02 15:04:05")))

	// Table header
	sb.WriteString("| Name | Description | Stars | Language |\n")
	sb.WriteString("|------|-------------|-------|----------|\n")

	// Table rows
	for _, repo := range repos {
		if repo.Fork {
			continue // Skip forked repositories
		}

		desc := repo.Description
		if desc == "" {
			desc = "-"
		}
		// Escape pipe characters in description
		desc = strings.ReplaceAll(desc, "|", "\\|")

		lang := repo.Language
		if lang == "" {
			lang = "-"
		}

		sb.WriteString(fmt.Sprintf("| [%s](%s) | %s | ⭐ %d | %s |\n",
			repo.Name,
			repo.HTMLURL,
			desc,
			repo.Stargazers,
			lang,
		))
	}

	// Statistics
	nonForkCount := 0
	totalStars := 0
	for _, repo := range repos {
		if !repo.Fork {
			nonForkCount++
			totalStars += repo.Stargazers
		}
	}

	sb.WriteString(fmt.Sprintf("\n**Statistics**: %d repositories, %d total stars", nonForkCount, totalStars))
	if nonForkCount > 0 {
		avgStars := float64(totalStars) / float64(nonForkCount)
		sb.WriteString(fmt.Sprintf(", %.1f average", avgStars))
	}
	sb.WriteString("\n")

	return sb.String()
}

func updateLocalFile(orgName, sectionContent string) error {
	outputPath := updateOrgStatusOutput
	if outputPath == "" {
		outputPath = ".github/README.md"
	}

	// Ensure directory exists
	dir := filepath.Dir(outputPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create directory %s: %w", dir, err)
	}

	// Read existing content or create new
	var newContent string
	if _, err := os.Stat(outputPath); err == nil {
		// File exists, update section
		existingContent, err := os.ReadFile(outputPath)
		if err != nil {
			return fmt.Errorf("failed to read existing file: %w", err)
		}
		newContent = updateSectionInContent(string(existingContent), sectionContent, updateOrgStatusSection)
	} else {
		// File doesn't exist, create full README
		newContent = generateFullREADME(orgName, sectionContent)
	}

	// Write file
	if err := os.WriteFile(outputPath, []byte(newContent), 0644); err != nil {
		return fmt.Errorf("failed to write README: %w", err)
	}

	fmt.Printf("Updated: %s\n", outputPath)

	// Git operations (unless skipped)
	if !updateOrgStatusSkipPush {
		if err := gitCommitAndPush(outputPath, orgName); err != nil {
			fmt.Printf("Warning: git operations failed: %v\n", err)
			fmt.Println("You may need to manually commit and push the changes.")
		}
	}

	return nil
}

func updateDotGitHubRepo(orgName, sectionContent string) error {
	// Create temp directory for .github repo
	tempDir := filepath.Join(os.TempDir(), fmt.Sprintf("github-repo-%s-%d", orgName, time.Now().Unix()))
	defer os.RemoveAll(tempDir)

	repoURL := fmt.Sprintf("https://github.com/%s/.github.git", orgName)
	repoDir := filepath.Join(tempDir, ".github")

	fmt.Printf("Cloning .github repository to: %s\n", repoDir)

	// Clone the repository
	cloneCmd := exec.Command("git", "clone", repoURL, repoDir)
	cloneCmd.Stdout = os.Stdout
	cloneCmd.Stderr = os.Stderr
	if err := cloneCmd.Run(); err != nil {
		return fmt.Errorf("failed to clone .github repository: %w\nNote: Make sure the .github repository exists and is accessible", err)
	}

	// Determine README path (profile/README.md or README.md)
	readmePath := filepath.Join(repoDir, "profile", "README.md")
	if _, err := os.Stat(readmePath); os.IsNotExist(err) {
		readmePath = filepath.Join(repoDir, "README.md")
	}

	// Read existing content or create new
	var newContent string
	if _, err := os.Stat(readmePath); err == nil {
		existingContent, err := os.ReadFile(readmePath)
		if err != nil {
			return fmt.Errorf("failed to read existing README: %w", err)
		}
		newContent = updateSectionInContent(string(existingContent), sectionContent, updateOrgStatusSection)
	} else {
		newContent = generateFullREADME(orgName, sectionContent)
	}

	// Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(readmePath), 0755); err != nil {
		return fmt.Errorf("failed to create directory: %w", err)
	}

	// Write file
	if err := os.WriteFile(readmePath, []byte(newContent), 0644); err != nil {
		return fmt.Errorf("failed to write README: %w", err)
	}

	fmt.Printf("Updated: %s\n", readmePath)

	// Git operations in .github repo
	if updateOrgStatusSkipPush {
		fmt.Println("Skipping git push (--skip-push used)")
		return nil
	}

	// Git add
	fmt.Printf("Running: git add README.md\n")
	addCmd := exec.Command("git", "-C", repoDir, "add", ".")
	addCmd.Stdout = os.Stdout
	addCmd.Stderr = os.Stderr
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("git add failed: %w", err)
	}

	// Check if there are changes to commit
	statusCmd := exec.Command("git", "-C", repoDir, "diff", "--cached", "--quiet")
	if err := statusCmd.Run(); err == nil {
		fmt.Println("No changes to commit.")
		return nil
	}

	// Git commit
	commitMsg := fmt.Sprintf("docs: update %s project list [skip ci]", orgName)
	fmt.Printf("Running: git commit -m \"%s\"\n", commitMsg)
	commitCmd := exec.Command("git", "-C", repoDir, "commit", "-m", commitMsg)
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		return fmt.Errorf("git commit failed: %w", err)
	}

	// Git push
	fmt.Println("Running: git push")
	pushCmd := exec.Command("git", "-C", repoDir, "push")
	pushCmd.Stdout = os.Stdout
	pushCmd.Stderr = os.Stderr
	if err := pushCmd.Run(); err != nil {
		return fmt.Errorf("git push failed: %w", err)
	}

	fmt.Println("Successfully committed and pushed changes to .github repository.")
	return nil
}

func updateSectionInContent(content, newSection, sectionName string) string {
	sectionHeader := "## " + sectionName
	
	// Find the section
	sectionStart := strings.Index(content, sectionHeader)
	if sectionStart == -1 {
		// Section doesn't exist, insert before the last section or at the end
		return insertSection(content, newSection)
	}

	// Find the end of this section (next ## section or end of file)
	sectionEnd := findSectionEnd(content, sectionStart)

	// Build new content: before section + new section + after section
	before := content[:sectionStart]
	after := ""
	if sectionEnd < len(content) {
		after = content[sectionEnd:]
	}

	// Clean up extra newlines
	before = strings.TrimRight(before, "\n")
	after = strings.TrimLeft(after, "\n")

	result := before
	if before != "" {
		result += "\n\n"
	}
	result += strings.TrimRight(newSection, "\n")
	if after != "" {
		result += "\n\n" + after
	}

	return result
}

func findSectionEnd(content string, sectionStart int) int {
	// Start searching after the section header line
	searchStart := sectionStart
	newlineIdx := strings.Index(content[searchStart:], "\n")
	if newlineIdx != -1 {
		searchStart += newlineIdx + 1
	}

	// Look for next ## section
	for i := searchStart; i < len(content)-2; i++ {
		if content[i] == '\n' && content[i+1] == '#' && content[i+2] == '#' {
			return i + 1
		}
	}

	return len(content)
}

func insertSection(content, newSection string) string {
	// Try to find a good place to insert (before last ## section or at end)
	lines := strings.Split(content, "\n")
	lastSectionIndex := -1

	for i, line := range lines {
		if strings.HasPrefix(line, "## ") {
			lastSectionIndex = i
		}
	}

	if lastSectionIndex >= 0 {
		// Insert before the last section
		newLines := make([]string, 0, len(lines)+10)
		newLines = append(newLines, lines[:lastSectionIndex]...)
		newLines = append(newLines, "")
		newLines = append(newLines, strings.Split(strings.TrimRight(newSection, "\n"), "\n")...)
		newLines = append(newLines, "")
		newLines = append(newLines, lines[lastSectionIndex:]...)
		return strings.Join(newLines, "\n")
	}

	// No sections found, append at end
	if !strings.HasSuffix(content, "\n") {
		content += "\n"
	}
	return content + "\n" + strings.TrimRight(newSection, "\n") + "\n"
}

func generateFullREADME(orgName, sectionContent string) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# %s\n\n", strings.Title(orgName)))
	sb.WriteString(fmt.Sprintf("Welcome to **%s**!\n\n", orgName))
	sb.WriteString(sectionContent)

	return sb.String()
}

func gitCommitAndPush(filePath, orgName string) error {
	// Check if we're in a git repository
	if _, err := exec.LookPath("git"); err != nil {
		return fmt.Errorf("git not found in PATH")
	}

	// Check if file is tracked by git
	cmd := exec.Command("git", "rev-parse", "--git-dir")
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("not in a git repository")
	}

	// Git add
	fmt.Printf("Running: git add %s\n", filePath)
	addCmd := exec.Command("git", "add", filePath)
	addCmd.Stdout = os.Stdout
	addCmd.Stderr = os.Stderr
	if err := addCmd.Run(); err != nil {
		return fmt.Errorf("git add failed: %w", err)
	}

	// Check if there are changes to commit
	statusCmd := exec.Command("git", "diff", "--cached", "--quiet")
	if err := statusCmd.Run(); err == nil {
		fmt.Println("No changes to commit.")
		return nil
	}

	// Git commit
	commitMsg := fmt.Sprintf("docs: update %s project list [skip ci]", orgName)
	fmt.Printf("Running: git commit -m \"%s\"\n", commitMsg)
	commitCmd := exec.Command("git", "commit", "-m", commitMsg)
	commitCmd.Stdout = os.Stdout
	commitCmd.Stderr = os.Stderr
	if err := commitCmd.Run(); err != nil {
		return fmt.Errorf("git commit failed: %w", err)
	}

	// Git push
	fmt.Println("Running: git push")
	pushCmd := exec.Command("git", "push")
	pushCmd.Stdout = os.Stdout
	pushCmd.Stderr = os.Stderr
	if err := pushCmd.Run(); err != nil {
		return fmt.Errorf("git push failed: %w", err)
	}

	fmt.Println("Successfully committed and pushed changes.")
	return nil
}

func init() {
	GitCmd.AddCommand(updateOrgStatusCmd)

	updateOrgStatusCmd.Flags().StringVarP(&updateOrgStatusOutput, "output", "o", ".github/README.md", "Output path for the README file (local mode)")
	updateOrgStatusCmd.Flags().BoolVar(&updateOrgStatusDryRun, "dry-run", false, "Print content without writing to file")
	updateOrgStatusCmd.Flags().BoolVar(&updateOrgStatusUpdateDotGitHub, "update-dot-github", false, "Update the organization's .github repository directly")
	updateOrgStatusCmd.Flags().StringVar(&updateOrgStatusSection, "section", "Project List", "Section name to update in README")
	updateOrgStatusCmd.Flags().BoolVar(&updateOrgStatusSkipPush, "skip-push", false, "Skip git commit and push")
}
