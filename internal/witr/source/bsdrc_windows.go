//go:build windows

package source

import "spark/pkg/witr/model"

func detectBsdRc(_ []model.Process) *model.Source {
	// windows doesn't use FreeBSD rc.d
	return nil
}
