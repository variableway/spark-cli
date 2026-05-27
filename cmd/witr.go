package cmd

import (
	"spark/internal/witr/app"
)

func init() {
	witrCmd := app.Root()
	rootCmd.AddCommand(witrCmd)
}
