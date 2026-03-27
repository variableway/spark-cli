package cmd

import (
	"fmt"
	"monolize/cmd/git"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var cfgFile string

var rootCmd = &cobra.Command{
	Use:   "spark",
	Short: "A CLI tool to manage multiple git repositories",
	Long: `Spark is a CLI application that helps you:
1. Update multiple git repositories to the latest version
2. Create a mono repo with all repositories as submodules
3. Manage all repositories with a single git command`,
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
		viper.AddConfigPath(home)
		viper.SetConfigName(".spark")
		viper.SetConfigType("yaml")
	}

	viper.AutomaticEnv()

	if err := viper.ReadInConfig(); err == nil {
		fmt.Fprintln(os.Stderr, "Using config file:", viper.ConfigFileUsed())
	}
}
