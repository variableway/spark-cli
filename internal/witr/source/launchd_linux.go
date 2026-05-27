//go:build linux

package source

import "spark/pkg/witr/model"

func detectLaunchd(_ []model.Process) *model.Source {
	return nil
}
