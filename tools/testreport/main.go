package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/onsi/ginkgo/v2/types"

	"spark/internal/testreport"
)

func main() {
	in := flag.String("in", "reports/ginkgo-report.json", "ginkgo --json-report output file")
	out := flag.String("out", "reports/test-report.html", "destination HTML report")
	flag.Parse()

	data, err := os.ReadFile(*in)
	if err != nil {
		fmt.Fprintf(os.Stderr, "read %s: %v\n", *in, err)
		os.Exit(1)
	}

	var reports []types.Report
	if err := json.Unmarshal(data, &reports); err != nil {
		fmt.Fprintf(os.Stderr, "parse %s: %v\n", *in, err)
		os.Exit(1)
	}

	if err := testreport.WriteFile(reports, *out); err != nil {
		fmt.Fprintf(os.Stderr, "write %s: %v\n", *out, err)
		os.Exit(1)
	}

	total, failed := 0, 0
	for _, r := range reports {
		total += len(r.SpecReports)
		for _, sr := range r.SpecReports {
			if !sr.State.Is(types.SpecStatePassed | types.SpecStateSkipped | types.SpecStatePending) {
				failed++
			}
		}
	}
	fmt.Printf("HTML report written to %s (%d specs, %d failed)\n", *out, total, failed)
}
