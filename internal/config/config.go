package config

import (
	"github.com/spf13/viper"
)

// Config holds the application configuration
type Config struct {
	Path          string `mapstructure:"path"`
	DefaultBranch string `mapstructure:"default_branch"`
	AutoCommit    bool   `mapstructure:"auto_commit"`
}

// Load loads the configuration from viper
func Load() (*Config, error) {
	var cfg Config

	// Set defaults
	viper.SetDefault("path", ".")
	viper.SetDefault("default_branch", "main")
	viper.SetDefault("auto_commit", true)

	// Read config
	if err := viper.ReadInConfig(); err != nil {
		// It's okay if there's no config file
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, err
		}
	}

	// Unmarshal config
	if err := viper.Unmarshal(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}
