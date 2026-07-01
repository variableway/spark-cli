package scanner

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS repos (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	path TEXT NOT NULL UNIQUE,
	name TEXT NOT NULL,
	remote_url TEXT NOT NULL,
	repo_type TEXT NOT NULL,
	owner TEXT NOT NULL,
	repo TEXT NOT NULL,
	description TEXT,
	stars INTEGER DEFAULT 0,
	forks INTEGER DEFAULT 0,
	language TEXT,
	updated_at TEXT,
	scanned_at TEXT NOT NULL
);
`

func DefaultDBPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, ".innate", "feeds.db"), nil
}

type Store struct {
	db *sql.DB
}

func OpenStore(dbPath string) (*Store, error) {
	if err := os.MkdirAll(filepath.Dir(dbPath), 0755); err != nil {
		return nil, fmt.Errorf("create database directory: %w", err)
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("open database: %w", err)
	}

	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("initialize schema: %w", err)
	}

	return &Store{db: db}, nil
}

func (s *Store) Close() error {
	if s.db == nil {
		return nil
	}
	return s.db.Close()
}

func (s *Store) SaveRepos(repos []RepoInfo) error {
	scannedAt := time.Now().UTC().Format(time.RFC3339)

	tx, err := s.db.Begin()
	if err != nil {
		return fmt.Errorf("begin transaction: %w", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
INSERT INTO repos (
	path, name, remote_url, repo_type, owner, repo,
	description, stars, forks, language, updated_at, scanned_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(path) DO UPDATE SET
	name = excluded.name,
	remote_url = excluded.remote_url,
	repo_type = excluded.repo_type,
	owner = excluded.owner,
	repo = excluded.repo,
	description = excluded.description,
	stars = excluded.stars,
	forks = excluded.forks,
	language = excluded.language,
	updated_at = excluded.updated_at,
	scanned_at = excluded.scanned_at
`)
	if err != nil {
		return fmt.Errorf("prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, repo := range repos {
		if _, err := stmt.Exec(
			repo.Path,
			repo.Name,
			repo.RemoteURL,
			repo.RepoType,
			repo.Owner,
			repo.Repo,
			repo.Description,
			repo.Stars,
			repo.Forks,
			repo.Language,
			repo.UpdatedAt,
			scannedAt,
		); err != nil {
			return fmt.Errorf("save repo %s: %w", repo.Path, err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit transaction: %w", err)
	}

	return nil
}
