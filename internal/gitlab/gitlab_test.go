package gitlab

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestIsGitLabURL(t *testing.T) {
	tests := []struct {
		input string
		want  bool
	}{
		{"https://gitlab.example.com/myorg/mygroup/mysubgroup", true},
		{"https://gitlab.com/mygroup/myproject", true},
		{"http://git.example.com/group", true},
		{"https://github.com/owner/repo", false},
		{"variableway", false},
		{"", false},
		{"github.com/owner", false},
		{"gitlab.example.com/myorg/mygroup/mysubgroup", true},
		{"gitlab.com/gitlab-com/gl-infra", true},
		{"gitlab.com/group/sub/project", true},
		{"variableway/spark-cli", false},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := IsGitLabURL(tt.input)
			if got != tt.want {
				t.Errorf("IsGitLabURL(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseGitLabURL(t *testing.T) {
	tests := []struct {
		name      string
		input     string
		wantBase  string
		wantGroup string
		wantErr   bool
	}{
		{
			name:      "self-hosted nested group",
			input:     "https://gitlab.example.com/myorg/mygroup/mysubgroup",
			wantBase:  "https://gitlab.example.com",
			wantGroup: "myorg/mygroup/mysubgroup",
		},
		{
			name:      "gitlab.com project",
			input:     "https://gitlab.com/mygroup/myproject",
			wantBase:  "https://gitlab.com",
			wantGroup: "mygroup/myproject",
		},
		{
			name:      "single group",
			input:     "http://git.example.com/group",
			wantBase:  "http://git.example.com",
			wantGroup: "group",
		},
		{
			name:      "with trailing slash",
			input:     "https://gitlab.example.com/myorg/mygroup/mysubgroup/",
			wantBase:  "https://gitlab.example.com",
			wantGroup: "myorg/mygroup/mysubgroup",
		},
		{
			name:    "no path",
			input:   "https://gitlab.example.com/",
			wantErr: true,
		},
		{
			name:    "empty path",
			input:   "https://gitlab.example.com",
			wantErr: true,
		},
		{
			name:      "scheme-less nested group",
			input:     "gitlab.com/gitlab-com/gl-infra",
			wantBase:  "https://gitlab.com",
			wantGroup: "gitlab-com/gl-infra",
		},
		{
			name:      "deeply nested group",
			input:     "https://gitlab.com/gitlab-com/gl-infra/k8s/workloads",
			wantBase:  "https://gitlab.com",
			wantGroup: "gitlab-com/gl-infra/k8s/workloads",
		},
		{
			name:    "scheme-less without path",
			input:   "gitlab.com",
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotBase, gotGroup, err := ParseGitLabURL(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseGitLabURL(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
				return
			}
			if gotBase != tt.wantBase {
				t.Errorf("ParseGitLabURL(%q) baseURL = %q, want %q", tt.input, gotBase, tt.wantBase)
			}
			if gotGroup != tt.wantGroup {
				t.Errorf("ParseGitLabURL(%q) groupPath = %q, want %q", tt.input, gotGroup, tt.wantGroup)
			}
		})
	}
}

func TestAPIGetGroupProjectsEncodesNestedPath(t *testing.T) {
	var gotPath string
	var gotQuery string

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.EscapedPath()
		gotQuery = r.URL.RawQuery
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, `[{"path":"archiver","path_with_namespace":"gitlab-com/gl-infra/archiver"}]`)
	}))
	defer srv.Close()

	projects, err := apiGetGroupProjects(srv.URL, "gitlab-com/gl-infra", "")
	if err != nil {
		t.Fatalf("apiGetGroupProjects() error = %v", err)
	}
	if len(projects) != 1 {
		t.Fatalf("apiGetGroupProjects() returned %d projects, want 1", len(projects))
	}

	wantPath := "/api/v4/groups/gitlab-com%2Fgl-infra/projects"
	if gotPath != wantPath {
		t.Errorf("request path = %q, want %q", gotPath, wantPath)
	}
	if !strings.Contains(gotQuery, "include_subgroups=true") {
		t.Errorf("request query = %q, want include_subgroups=true", gotQuery)
	}
}

func TestDetectAccountTypeNestedGroup(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.EscapedPath() == "/api/v4/groups/gitlab-com%2Fgl-infra" {
			w.WriteHeader(http.StatusOK)
			fmt.Fprint(w, `{"id":1}`)
			return
		}
		w.WriteHeader(http.StatusNotFound)
	}))
	defer srv.Close()

	accountType, resolvedPath, err := detectAccountType(srv.URL, "gitlab-com/gl-infra", "", "")
	if err != nil {
		t.Fatalf("detectAccountType() error = %v", err)
	}
	if accountType != "group" {
		t.Errorf("accountType = %q, want group", accountType)
	}
	if resolvedPath != "gitlab-com/gl-infra" {
		t.Errorf("resolvedPath = %q, want gitlab-com/gl-infra", resolvedPath)
	}
}

func TestDetectAccountTypeAuthenticationFailed(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		fmt.Fprint(w, `{"message":"401 Unauthorized"}`)
	}))
	defer srv.Close()

	_, _, err := detectAccountType(srv.URL, "gitlab-com/gl-infra", "expired-token", TokenSourceConfig)
	if err == nil {
		t.Fatal("detectAccountType() error = nil, want authentication error")
	}
	if !strings.Contains(err.Error(), "authentication failed") {
		t.Errorf("detectAccountType() error = %q, want authentication failure hint", err)
	}
	if !strings.Contains(err.Error(), TokenSourceConfig) {
		t.Errorf("detectAccountType() error = %q, want the token source %q", err, TokenSourceConfig)
	}
}

func TestDetectAccountTypeWithoutCredentials(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		fmt.Fprint(w, `{"message":"404 Not Found"}`)
	}))
	defer srv.Close()

	_, _, err := detectAccountType(srv.URL, "gitlab-com/gl-infra", "", "")
	if err == nil {
		t.Fatal("detectAccountType() error = nil, want not-found error")
	}
	if !strings.Contains(err.Error(), "without credentials") {
		t.Errorf("detectAccountType() error = %q, want missing-credentials hint", err)
	}
}

func TestProjectRelativePath(t *testing.T) {
	tests := []struct {
		name      string
		project   Project
		namespace string
		want      string
	}{
		{
			name:      "nested group project",
			project:   Project{Path: "archiver", PathWithNamespace: "gitlab-com/gl-infra/archiver"},
			namespace: "gitlab-com/gl-infra",
			want:      "archiver",
		},
		{
			name:      "subgroup project keeps subgroup",
			project:   Project{Path: "argocd-tenant-plugin", PathWithNamespace: "gitlab-com/gl-infra/observability/tenant-observability/argocd-tenant-plugin"},
			namespace: "gitlab-com/gl-infra",
			want:      "observability/tenant-observability/argocd-tenant-plugin",
		},
		{
			name:      "resolved parent group keeps subgroup",
			project:   Project{Path: "archiver", PathWithNamespace: "gitlab-com/gl-infra/archiver"},
			namespace: "gitlab-com",
			want:      "gl-infra/archiver",
		},
		{
			name:      "user namespace",
			project:   Project{Path: "gitaly", PathWithNamespace: "someuser/gitaly"},
			namespace: "someuser",
			want:      "gitaly",
		},
		{
			name:      "namespace not matching falls back to path",
			project:   Project{Path: "gitlab", PathWithNamespace: "gitlab-org/gitlab"},
			namespace: "gitlab-com",
			want:      "gitlab",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ProjectRelativePath(tt.project, tt.namespace)
			if got != tt.want {
				t.Errorf("ProjectRelativePath(%q, %q) = %q, want %q", tt.project.PathWithNamespace, tt.namespace, got, tt.want)
			}
		})
	}
}

func TestEscapePath(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"gitlab-com/gl-infra", "gitlab-com%2Fgl-infra"},
		{"mygroup", "mygroup"},
		{"my-group/sub_group", "my-group%2Fsub_group"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := escapePath(tt.input)
			if got != tt.want {
				t.Errorf("escapePath(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestExtractHost(t *testing.T) {
	tests := []struct {
		input string
		want  string
	}{
		{"https://gitlab.example.com", "gitlab.example.com"},
		{"https://gitlab.com", "gitlab.com"},
		{"http://git.example.com:8080", "git.example.com:8080"},
		{"https://gitlab.com/", "gitlab.com"},
		{"gitlab.com", "gitlab.com"},
		{"GitLab.Example.com", "gitlab.example.com"},
		{"gitlab.example.com/myorg/mygroup", "gitlab.example.com"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := ExtractHost(tt.input)
			if got != tt.want {
				t.Errorf("ExtractHost(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
