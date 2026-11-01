package hub

import (
	"fmt"
	"spark/internal/collection"

	"github.com/spf13/cobra"
)

var (
	outputFile string
	skipAPI    bool
	category   string
	mergeFile  string
	deep       bool
)

var scanCmd = &cobra.Command{
	Use:   "scan [path]",
	Short: "Scan git repositories into innate-apps registry format",
	Long: `Recursively scan a directory for git repositories with an origin
remote, fetch GitHub metadata (description, language, visibility), and emit
them in the innate-apps registry format (registry/apps.json).

Curated fields (title, category, status) from an existing registry file are
preserved when merging with --merge.

Examples:
  spark hub scan /path/to/innate-apps
  spark hub scan . -o registry/apps.json --merge registry/apps.json
  spark hub scan . --skip-api --category reference`,
	Args: cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		root := "."
		if len(args) > 0 {
			root = args[0]
		}

		maxDepth := 1
		if deep {
			maxDepth = 0
		}

		discovered, err := collection.Scan(root, skipAPI, maxDepth)
		if err != nil {
			return err
		}

		if category != "" {
			for i := range discovered {
				discovered[i].Category = category
			}
		}

		existing := []collection.Entry{}
		if mergeFile != "" {
			reg, err := collection.Read(mergeFile)
			if err != nil {
				return err
			}
			existing = reg.Collections
		}

		entries := collection.Merge(existing, discovered)

		reg := &collection.Registry{
			Schema:      "./schema.json",
			Version:     1,
			Collections: entries,
		}

		out := outputFile
		if out == "" && mergeFile != "" {
			out = mergeFile
		}

		if err := collection.Write(out, reg); err != nil {
			return err
		}

		if out != "" {
			fmt.Printf("Wrote %d collection(s) to %s\n", len(entries), out)
		}
		return nil
	},
}

func init() {
	scanCmd.Flags().StringVarP(&outputFile, "output", "o", "", "Write JSON to a file (default: stdout)")
	scanCmd.Flags().StringVar(&mergeFile, "merge", "", "Merge with an existing registry file, preserving curated fields")
	scanCmd.Flags().BoolVar(&skipAPI, "skip-api", false, "Skip GitHub API calls, use local git info only")
	scanCmd.Flags().BoolVar(&deep, "deep", false, "Include nested repositories (default: top-level only)")
	scanCmd.Flags().StringVar(&category, "category", "", "Set category for discovered entries (base|app|reference)")
}
