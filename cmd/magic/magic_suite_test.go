package magic

import (
	"testing"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

func TestMagic(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Magic Suite")
}
