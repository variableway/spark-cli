package registry

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type FlattenMove struct {
	From string
	To   string
}

type FlattenConflict struct {
	From   string
	To     string
	Reason string
}

type FlattenResult struct {
	Moves     []FlattenMove
	Conflicts []FlattenConflict
}

// Flatten moves repositories nested deeper than two levels (category/repo)
// up into the two-level layout. Depth-1 and depth-2 repositories are left
// untouched. When the target path already exists, the repository stays in
// place and the conflict is reported instead of overwriting anything.
func Flatten(root string) (*FlattenResult, error) {
	absRoot, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}

	projects, err := Scan(absRoot)
	if err != nil {
		return nil, err
	}

	sort.SliceStable(projects, func(i, j int) bool {
		return depth(projects[i].Path) > depth(projects[j].Path)
	})

	result := &FlattenResult{}
	claimed := map[string]bool{}

	for _, p := range projects {
		if depth(p.Path) <= 2 {
			continue
		}

		rel := filepath.FromSlash(p.Path)
		targetRel := filepath.Join(strings.Split(p.Path, "/")[0], filepath.Base(rel))
		target := filepath.Join(absRoot, targetRel)

		if _, err := os.Stat(target); err == nil {
			result.Conflicts = append(result.Conflicts, FlattenConflict{
				From:   p.Path,
				To:     filepath.ToSlash(targetRel),
				Reason: "target already exists",
			})
			continue
		}
		if claimed[filepath.ToSlash(targetRel)] {
			result.Conflicts = append(result.Conflicts, FlattenConflict{
				From:   p.Path,
				To:     filepath.ToSlash(targetRel),
				Reason: "target claimed by another repository in this run",
			})
			continue
		}

		src := filepath.Join(absRoot, rel)
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return nil, fmt.Errorf("flatten %s: %w", p.Path, err)
		}
		if err := os.Rename(src, target); err != nil {
			return nil, fmt.Errorf("flatten %s: %w", p.Path, err)
		}
		claimed[filepath.ToSlash(targetRel)] = true
		result.Moves = append(result.Moves, FlattenMove{
			From: p.Path,
			To:   filepath.ToSlash(targetRel),
		})

		removeEmptyParents(absRoot, filepath.Dir(src))
	}

	return result, nil
}

func depth(rel string) int {
	return strings.Count(rel, "/") + 1
}

func removeEmptyParents(root, dir string) {
	for dir != root && strings.HasPrefix(dir, root) {
		if err := os.Remove(dir); err != nil {
			return
		}
		dir = filepath.Dir(dir)
	}
}
