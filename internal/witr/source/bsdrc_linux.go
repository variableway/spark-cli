//go:build linux

package source

import "spark/pkg/witr/model"

func detectBsdRc(_ []model.Process) *model.Source {
	// Linux doesn't use FreeBSD rc.d
	return nil
}
