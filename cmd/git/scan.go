package git

import (
	"fmt"
	"os"
	"path/filepath"

	"spark/internal/git/scanner"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var (
	scanDBPath  string
	scanSkipAPI bool
)

var scanCmd = &cobra.Command{
	Use:   "scan [folder-path]",
	Short: "Scan folders for git repositories and save to SQLite",
	Long: `Recursively scan a folder for git repositories, optionally fetch metadata
from GitHub/GitLab APIs, and save results to a SQLite database.

The default database path is ~/.innate/feeds.db and can be overridden via
the --db flag or the 'git.scanner.db' config key in ~/.spark.yaml.`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		folderPath := "."
		if len(args) > 0 {
			folderPath = args[0]
		}

		absPath, err := filepath.Abs(folderPath)
		if err != nil {
			return fmt.Errorf("resolve path: %w", err)
		}

		dbPath := scanDBPath
		if dbPath == "" {
			dbPath = viper.GetString("git.scanner.db")
		}
		if dbPath == "" {
			dbPath, err = scanner.DefaultDBPath()
			if err != nil {
				return fmt.Errorf("resolve default database path: %w", err)
			}
		} else if len(dbPath) >= 2 && dbPath[0] == '~' && (dbPath[1] == '/' || dbPath[1] == '\\') {
			home, err := os.UserHomeDir()
			if err != nil {
				return fmt.Errorf("resolve home directory: %w", err)
			}
			dbPath = filepath.Join(home, dbPath[2:])
		}

		fmt.Printf("Scanning folder: %s\n", absPath)
		fmt.Println("Looking for git repositories...")
		if !scanSkipAPI {
			fmt.Println("Fetching repository information from APIs...")
		}

		repos, err := scanner.Scan(absPath, scanner.Options{SkipAPI: scanSkipAPI})
		if err != nil {
			return err
		}

		if len(repos) == 0 {
			fmt.Println("No git repositories found.")
			return nil
		}

		fmt.Printf("\nFound %d repositories\n", len(repos))

		store, err := scanner.OpenStore(dbPath)
		if err != nil {
			return err
		}
		defer store.Close()

		if err := store.SaveRepos(repos); err != nil {
			return err
		}

		fmt.Printf("\nSaved %d repositories to: %s\n", len(repos), dbPath)
		printScanSummary(repos)

		return nil
	},
}

func printScanSummary(repos []scanner.RepoInfo) {
	fmt.Println("\nSummary:")

	reposByType := make(map[string]int)
	for _, repo := range repos {
		reposByType[repo.RepoType]++
	}

	for repoType, count := range reposByType {
		fmt.Printf("  - %s: %d repositories\n", repoType, count)
	}

	totalStars := 0
	for _, repo := range repos {
		totalStars += repo.Stars
	}
	if totalStars > 0 {
		fmt.Printf("  - Total stars: %d\n", totalStars)
	}
}

func init() {
	scanCmd.Flags().StringVarP(&scanDBPath, "db", "d", "", "SQLite database path (default: ~/.innate/feeds.db)")
	scanCmd.Flags().BoolVar(&scanSkipAPI, "skip-api", false, "Skip API calls, only scan local repos")

	viper.SetDefault("git.scanner.db", "")
	viper.BindPFlag("git.scanner.db", scanCmd.Flags().Lookup("db"))

	GitCmd.AddCommand(scanCmd)
}
