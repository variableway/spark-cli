package magic

import (
	"runtime"

	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"
)

var _ = Describe("FlushDNS", func() {
	Describe("getDNSCommands", func() {
		Context("on macOS", func() {
			It("should return dscacheutil and killall commands", func() {
				commands, err := getDNSCommands("darwin")
				Expect(err).NotTo(HaveOccurred())
				Expect(commands).To(HaveLen(2))
				Expect(commands[0]).To(Equal([]string{"sudo", "dscacheutil", "-flushcache"}))
				Expect(commands[1]).To(Equal([]string{"sudo", "killall", "-HUP", "mDNSResponder"}))
			})
		})

		Context("on Windows", func() {
			It("should return ipconfig flushdns command", func() {
				commands, err := getDNSCommands("windows")
				Expect(err).NotTo(HaveOccurred())
				Expect(commands).To(HaveLen(1))
				Expect(commands[0]).To(Equal([]string{"ipconfig", "/flushdns"}))
			})
		})

		Context("on Linux", func() {
			It("should return multiple flush methods", func() {
				commands, err := getDNSCommands("linux")
				Expect(err).NotTo(HaveOccurred())
				Expect(commands).To(HaveLen(4))
				Expect(commands[0]).To(Equal([]string{"sudo", "systemctl", "restart", "systemd-resolved"}))
				Expect(commands[1]).To(Equal([]string{"sudo", "service", "nscd", "restart"}))
				Expect(commands[2]).To(Equal([]string{"sudo", "service", "dnsmasq", "restart"}))
				Expect(commands[3]).To(Equal([]string{"sudo", "rndc", "flush"}))
			})
		})

		Context("on unsupported OS", func() {
			It("should return an error", func() {
				_, err := getDNSCommands("freebsd")
				Expect(err).To(HaveOccurred())
				Expect(err.Error()).To(ContainSubstring("unsupported operating system: freebsd"))
			})
		})
	})

	Describe("flushDNS routing", func() {
		Context("on the current platform", func() {
			It("should not return unsupported OS error", func() {
				err := flushDNS()
				if runtime.GOOS == "darwin" || runtime.GOOS == "windows" || runtime.GOOS == "linux" {
					Expect(err).NotTo(HaveOccurred())
				}
			})
		})
	})
})
