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

var registerCmd = &cobra.Command{
	Use:   "scan [path]",
	Short: "Scan apps you develop into an innate-apps collections catalog",
	Long: `Scan a directory of apps you develop. Repositories with an origin
remote are enriched from the GitHub API (description, language, visibility)
and written as an innate-apps collections catalog (registry/apps.json).

This is not the references registry. Reference checkouts belong under
spark hub registry.

Curated fields (title, category, status, url, description) from an existing
catalog are preserved when merging with --merge.

Examples:
  spark hub collections scan /path/to/innate-apps
  spark hub collections scan . -o registry/apps.json --merge registry/apps.json
  spark hub collections scan . --skip-api --category app`,
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
	registerCmd.Flags().StringVarP(&outputFile, "output", "o", "", "Write JSON to a file (default: stdout)")
	registerCmd.Flags().StringVar(&mergeFile, "merge", "", "Merge with an existing collections file, preserving curated fields")
	registerCmd.Flags().BoolVar(&skipAPI, "skip-api", false, "Skip GitHub API calls, use local git info only")
	registerCmd.Flags().BoolVar(&deep, "deep", false, "Include nested repositories (default: top-level only)")
	registerCmd.Flags().StringVar(&category, "category", "", "Set category for discovered entries (base|app|reference)")
}
