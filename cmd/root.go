package cmd

import (
	"fmt"
	"monolize/cmd/git"
	"monolize/cmd/magic"
	"monolize/cmd/script"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var cfgFile string

var rootCmd = &cobra.Command{
	Use:   "spark",
	Short: "A CLI tool to manage multiple git repositories and scripts",
	Long: `Spark is a CLI application that helps you:
1. Update multiple git repositories to the latest version
2. Create a mono repo with all repositories as submodules
3. Manage all repositories with a single git command
4. Execute custom scripts for automation`,
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.spark.yaml)")
	rootCmd.PersistentFlags().StringSliceP("path", "p", []string{"."}, "Path to the directory containing git repositories")
	viper.BindPFlag("repo-path", rootCmd.PersistentFlags().Lookup("path"))
	rootCmd.AddCommand(git.GitCmd)
	rootCmd.AddCommand(magic.MagicCmd)
	rootCmd.AddCommand(script.ScriptCmd)
}

func initConfig() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, err := os.UserHomeDir()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		migrateOldConfig(home)
		viper.AddConfigPath(home)
		viper.SetConfigName(".spark")
		viper.SetConfigType("yaml")
	}

	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		fmt.Fprintln(os.Stderr, "Using config file:", viper.ConfigFileUsed())
	}
}

func migrateOldConfig(home string) {
	oldPath := filepath.Join(home, ".monolize.yaml")
	newPath := filepath.Join(home, ".spark.yaml")

	if _, err := os.Stat(oldPath); err == nil {
		if _, err := os.Stat(newPath); os.IsNotExist(err) {
			if err := os.Rename(oldPath, newPath); err == nil {
				fmt.Fprintf(os.Stderr, "Migrated old config file: %s -> %s\n", oldPath, newPath)
			}
		}
	}
}
