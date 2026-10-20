package testreport_test

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/onsi/ginkgo/v2/types"
	. "github.com/onsi/ginkgo/v2"
	. "github.com/onsi/gomega"

	"spark/internal/testreport"
)

func TestTestreport(t *testing.T) {
	RegisterFailHandler(Fail)
	RunSpecs(t, "Testreport Suite")
}

func sampleReports() []types.Report {
	return []types.Report{
		{
			SuiteDescription: "Config Suite",
			SuiteSucceeded:   true,
			StartTime:        time.Now(),
			EndTime:          time.Now().Add(2 * time.Second),
			RunTime:          2 * time.Second,
			SpecReports: types.SpecReports{
				{
					ContainerHierarchyTexts: []string{"Config", "Load"},
					LeafNodeText:            "reads the default path",
					State:                   types.SpecStatePassed,
					RunTime:                 time.Millisecond * 12,
				},
				{
					ContainerHierarchyTexts: []string{"Config", "Load"},
					LeafNodeText:            "fails on bad yaml",
					State:                   types.SpecStateFailed,
					RunTime:                 time.Millisecond * 5,
					Failure:                 types.Failure{Message: "expected map, got string"},
				},
				{
					ContainerHierarchyTexts: []string{"Config", "Migrate"},
					LeafNodeText:            "skips when no old file",
					State:                   types.SpecStateSkipped,
					Failure:                 types.Failure{Message: "not applicable"},
				},
				{
					ContainerHierarchyTexts: []string{"Config", "Migrate"},
					LeafNodeText:            "pending spec",
					State:                   types.SpecStatePending,
				},
			},
		},
		{
			SuiteDescription: "Git Suite",
			SuiteSucceeded:   false,
			RunTime:          3 * time.Second,
			SpecReports: types.SpecReports{
				{
					LeafNodeText: "clones a repository",
					State:        types.SpecStatePassed,
				},
			},
		},
	}
}

var _ = Describe("Render", func() {
	It("produces an HTML document with suites and every spec", func() {
		html, err := testreport.Render(sampleReports())
		Expect(err).NotTo(HaveOccurred())
		Expect(html).To(ContainSubstring("<!DOCTYPE html>"))
		Expect(html).To(ContainSubstring("Config Suite"))
		Expect(html).To(ContainSubstring("Git Suite"))
		Expect(html).To(ContainSubstring("reads the default path"))
		Expect(html).To(ContainSubstring("fails on bad yaml"))
		Expect(html).To(ContainSubstring("skips when no old file"))
		Expect(html).To(ContainSubstring("clones a repository"))
		Expect(html).To(ContainSubstring(`class="badge failed"`))
		Expect(html).To(ContainSubstring("expected map, got string"))
	})

	It("escapes HTML in spec text and failure messages", func() {
		reports := []types.Report{{
			SuiteDescription: "Escaping",
			SuiteSucceeded:   false,
			SpecReports: types.SpecReports{{
				LeafNodeText: "uses <script>alert(1)</script>",
				State:        types.SpecStateFailed,
				Failure:      types.Failure{Message: "<b> boom"},
			}},
		}}
		html, err := testreport.Render(reports)
		Expect(err).NotTo(HaveOccurred())
		Expect(html).NotTo(ContainSubstring("<script>alert(1)</script>"))
		Expect(html).To(ContainSubstring("&lt;script&gt;"))
		Expect(html).To(ContainSubstring("&lt;b&gt; boom"))
	})

	It("reports correct totals in the summary cards", func() {
		html, err := testreport.Render(sampleReports())
		Expect(err).NotTo(HaveOccurred())
		Expect(html).To(ContainSubstring(`<div class="num">2</div><div class="lbl">Suites</div>`))
		Expect(html).To(ContainSubstring(`<div class="num">5</div><div class="lbl">Specs</div>`))
	})

	It("renders an empty report without error", func() {
		html, err := testreport.Render(nil)
		Expect(err).NotTo(HaveOccurred())
		Expect(html).To(ContainSubstring("Ginkgo Test Report"))
	})
})

var _ = Describe("WriteFile", func() {
	It("writes the HTML file and creates parent directories", func() {
		dest := filepath.Join(GinkgoT().TempDir(), "nested", "report.html")
		Expect(testreport.WriteFile(sampleReports(), dest)).To(Succeed())

		data, err := os.ReadFile(dest)
		Expect(err).NotTo(HaveOccurred())
		Expect(strings.Contains(string(data), "Config Suite")).To(BeTrue())
	})
})
