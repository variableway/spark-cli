//go:build darwin

package source

import "spark/pkg/witr/model"

func detectSystemd(_ []model.Process) *model.Source {
	return nil
}

// IsSystemdRunning always returns false on macOS.
func IsSystemdRunning() bool { return false }
