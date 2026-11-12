package registry

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// Categorize groups flat scan results into the canonical three-level layout:
//
//	<category>/<subcategory>/<project>     (e.g. skills/agent/taste-skill)
//
// Rules:
//   - categories are the folder's immediate subdirectories (sorted), so empty
//     categories such as products/plugins still appear in the registry;
//   - every category always gets an "others" subcategory;
//   - a project directly under a category (<category>/<project>) has no
//     subcategory and lands in that category's "others";
//   - deeper projects (e.g. a project vendoring nested clones) keep their full
//     path but are grouped by their first two segments;
//   - a project directly under the folder root has no category at all and is
//     returned as skipped for the caller to warn about (it must be moved into
//     a category first — the registry only ever has the three real categories).
//
// It returns (nil, projects) when the folder has no category directories, i.e.
// the layout is not categorized — the caller then falls back to the legacy
// flat registry format.
func Categorize(folder string, projects []Project) (groups []Category, skipped []Project, err error) {
	cats, err := immediateSubdirs(folder)
	if err != nil {
		return nil, nil, fmt.Errorf("list categories in %s: %w", folder, err)
	}
	if len(cats) == 0 {
		// Not a categorized layout (legacy "flat" folder): report every project
		// as unclassified so the caller keeps the old flat format.
		return nil, projects, nil
	}
	catSet := make(map[string]bool, len(cats))
	for _, c := range cats {
		catSet[c] = true
	}

	type key struct{ cat, sub string }
	var order []key
	buckets := map[key][]Project{}

	for _, p := range projects {
		segs := strings.Split(strings.Trim(p.Path, "/"), "/")
		var cat, sub string
		switch {
		case len(segs) >= 3:
			cat, sub = segs[0], segs[1]
		case len(segs) == 2:
			cat, sub = segs[0], OthersSubcategory
		default:
			skipped = append(skipped, p)
			continue
		}
		if !catSet[cat] {
			skipped = append(skipped, p)
			continue
		}
		k := key{cat: cat, sub: sub}
		if _, ok := buckets[k]; !ok {
			order = append(order, k)
		}
		buckets[k] = append(buckets[k], p)
	}

	groups = make([]Category, 0, len(cats))
	for _, cat := range cats {
		diskSubs, err := immediateSubdirs(filepath.Join(folder, cat))
		if err != nil {
			return nil, nil, fmt.Errorf("list subcategories of %s: %w", cat, err)
		}
		subSet := map[string]bool{}
		var subNames []string
		for _, s := range diskSubs {
			subSet[s] = true
			subNames = append(subNames, s)
		}
		for _, k := range order {
			if k.cat == cat && !subSet[k.sub] {
				subSet[k.sub] = true
				subNames = append(subNames, k.sub)
			}
		}
		if !subSet[OthersSubcategory] {
			// The default bucket always exists, even before any project needs it.
			subNames = append(subNames, OthersSubcategory)
		}
		sortSubcategories(subNames)

		cat := Category{Name: cat, Subcategories: make([]Subcategory, 0, len(subNames))}
		for _, sub := range subNames {
			projs := buckets[key{cat: cat.Name, sub: sub}]
			sorted := make([]Project, len(projs))
			copy(sorted, projs)
			sort.SliceStable(sorted, func(i, j int) bool { return sorted[i].Path < sorted[j].Path })
			cat.Subcategories = append(cat.Subcategories, Subcategory{Name: sub, Projects: sorted})
		}
		groups = append(groups, cat)
	}
	return groups, skipped, nil
}

// sortSubcategories orders alphabetically but always keeps "others" last.
func sortSubcategories(names []string) {
	sort.SliceStable(names, func(i, j int) bool {
		if names[i] == OthersSubcategory {
			return false
		}
		if names[j] == OthersSubcategory {
			return true
		}
		return names[i] < names[j]
	})
}

// immediateSubdirs returns the sorted names of the immediate subdirectories
// that are NOT git repositories. A directory holding a `.git` is a project, not
// a category/subcategory: root-level repos must not become categories and a
// repo directly under a category belongs in that category's "others" bucket.
func immediateSubdirs(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, e := range entries {
		if !e.IsDir() || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		if isGitRepo(filepath.Join(dir, e.Name())) {
			continue
		}
		out = append(out, e.Name())
	}
	sort.Strings(out)
	return out, nil
}
