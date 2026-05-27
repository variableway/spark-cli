//go:build freebsd

package source

import "spark/pkg/witr/model"

func detectLaunchd(_ []model.Process) *model.Source {
	// FreeBSD doesn't use launchd
	return nil
}
