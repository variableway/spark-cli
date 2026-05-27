//go:build windows

package source

import "spark/pkg/witr/model"

func detectSystemd(ancestry []model.Process) *model.Source {
	return nil
}

// IsSystemdRunning always returns false on Windows.
func IsSystemdRunning() bool { return false }
