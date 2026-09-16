package git

import (
	"testing"

	"spark/internal/gitlab"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

func TestResolveGitLabToken(t *testing.T) {
	tests := []struct {
		name       string
		configHost string
		configUser string
		envToken   string
		flagToken  string
		targetHost string
		wantToken  string
		wantSource string
	}{
		{
			name:       "flag token is never scoped",
			configHost: "git.cew.io",
			flagToken:  "flag-token",
			targetHost: "gitlab.com",
			wantToken:  "flag-token",
			wantSource: gitlab.TokenSourceFlag,
		},
		{
			name:       "config token used when host matches",
			configHost: "git.cew.io",
			configUser: "glpat-config",
			targetHost: "git.cew.io",
			wantToken:  "glpat-config",
			wantSource: gitlab.TokenSourceConfig,
		},
		{
			name:       "config token used when host is given as URL",
			configHost: "https://git.cew.io/",
			configUser: "glpat-config",
			targetHost: "git.cew.io",
			wantToken:  "glpat-config",
			wantSource: gitlab.TokenSourceConfig,
		},
		{
			name:       "config token skipped for another host",
			configHost: "git.cew.io",
			configUser: "glpat-config",
			targetHost: "gitlab.com",
			wantToken:  "",
			wantSource: "",
		},
		{
			name:       "config token used when no host is configured",
			configUser: "glpat-config",
			targetHost: "gitlab.com",
			wantToken:  "glpat-config",
			wantSource: gitlab.TokenSourceConfig,
		},
		{
			name:       "config token wins over env token",
			configUser: "glpat-config",
			envToken:   "glpat-env",
			targetHost: "gitlab.com",
			wantToken:  "glpat-config",
			wantSource: gitlab.TokenSourceConfig,
		},
		{
			name:       "env token used when host matches",
			configHost: "git.cew.io",
			envToken:   "glpat-env",
			targetHost: "git.cew.io",
			wantToken:  "glpat-env",
			wantSource: gitlab.TokenSourceEnv,
		},
		{
			name:       "env token skipped for another host",
			configHost: "git.cew.io",
			envToken:   "glpat-env",
			targetHost: "gitlab.com",
			wantToken:  "",
			wantSource: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Cleanup(viper.Reset)
			t.Setenv("GITLAB_TOKEN", tt.envToken)
			t.Setenv("GITLAB_PRIVATE_TOKEN", "")

			viper.Set("gitlab.host", tt.configHost)
			viper.Set("gitlab.token", tt.configUser)

			cmd := &cobra.Command{Use: "batch-clone"}
			cmd.Flags().String("token", "", "")
			if tt.flagToken != "" {
				if err := cmd.Flags().Set("token", tt.flagToken); err != nil {
					t.Fatalf("failed to set token flag: %v", err)
				}
			}

			token, source := resolveGitLabToken(cmd, tt.targetHost)
			if token != tt.wantToken {
				t.Errorf("resolveGitLabToken() token = %q, want %q", token, tt.wantToken)
			}
			if source != tt.wantSource {
				t.Errorf("resolveGitLabToken() source = %q, want %q", source, tt.wantSource)
			}
		})
	}
}
