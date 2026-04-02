package config_test

import (
	"monolize/internal/config"
	"os"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
	"github.com/spf13/viper"
)

var _ = Describe("Config", func() {
	Describe("Load", func() {
		BeforeEach(func() {
			viper.Reset()
		})

		Context("with default values", func() {
			It("should load default configuration", func() {
				cfg, err := config.Load()
				Expect(err).NotTo(HaveOccurred())
				Expect(cfg.Path).To(Equal("."))
				Expect(cfg.DefaultBranch).To(Equal("main"))
				Expect(cfg.AutoCommit).To(BeTrue())
			})
		})

		Context("with a configuration file", func() {
			BeforeEach(func() {
				// Create a temporary config file
				configContent := `
path: /tmp/repos
default_branch: develop
auto_commit: false
`
				err := os.WriteFile(".spark.yaml", []byte(configContent), 0644)
				Expect(err).NotTo(HaveOccurred())

				viper.SetConfigFile(".spark.yaml")
			})

			AfterEach(func() {
				os.Remove(".spark.yaml")
			})

			It("should load values from the configuration file", func() {
				cfg, err := config.Load()
				Expect(err).NotTo(HaveOccurred())
				Expect(cfg.Path).To(Equal("/tmp/repos"))
				Expect(cfg.DefaultBranch).To(Equal("develop"))
				Expect(cfg.AutoCommit).To(BeFalse())
			})
		})
	})
})
