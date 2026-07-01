package scanner

type RepoInfo struct {
	Path        string
	Name        string
	RemoteURL   string
	RepoType    string
	Owner       string
	Repo        string
	Description string
	Stars       int
	Forks       int
	Language    string
	UpdatedAt   string
}

type Options struct {
	SkipAPI bool
}
