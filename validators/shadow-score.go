// Shadow Score Reference Validator (Go)
// Computes Shadow Score from test result files (JSON format).
// Conforms to Shadow Score Spec v2.0.0.
//
// Usage:
//
//	go run shadow-score.go --sealed sealed-results.json --open open-results.json
//	go run shadow-score.go --sealed sealed-results.json --threshold 15
//	go run shadow-score.go --sealed sealed-results.json --format summary
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"strconv"
)

const specVersion = "2.0.0"

var categories = []string{"happy_path", "edge_case", "error_handling", "security"}

type levelDef struct {
	threshold float64
	name      string
	indicator string
}

var levels = []levelDef{
	{0, "perfect", "✅"},
	{15, "minor", "🟢"},
	{30, "moderate", "🟡"},
	{50, "significant", "🟠"},
	{100, "critical", "🔴"},
}

// TestResult mirrors one entry in the "tests" array of the input JSON.
type TestResult struct {
	Name     string `json:"name"`
	Status   string `json:"status"`
	Category string `json:"category,omitempty"`
	Expected string `json:"expected,omitempty"`
	Actual   string `json:"actual,omitempty"`
	Message  string `json:"message,omitempty"`
}

type inputFile struct {
	Tests []TestResult `json:"tests"`
}

// Failure is a single failure entry in the output report.
type Failure struct {
	TestName string `json:"test_name"`
	Category string `json:"category"`
	Expected string `json:"expected"`
	Actual   string `json:"actual"`
	Message  string `json:"message"`
}

type reportSummary struct {
	ShadowScore float64 `json:"shadow_score"`
	Level    string  `json:"level"`
}

type testStats struct {
	Total  int `json:"total"`
	Passed int `json:"passed"`
	Failed int `json:"failed"`
}

// CategoryComparison holds per-category sealed vs open counts.
type CategoryComparison struct {
	Sealed int `json:"sealed"`
	Open   int `json:"open"`
	Delta  int `json:"delta"`
}

// Report is the top-level JSON output structure.
type Report struct {
	SpecVersion        string                        `json:"shadow_score_spec_version"`
	Report             reportSummary                 `json:"report"`
	SealedTests        testStats                     `json:"sealed_tests"`
	OpenTests          *testStats                    `json:"open_tests,omitempty"`
	Failures           []Failure                     `json:"failures"`
	CoverageComparison map[string]CategoryComparison `json:"coverage_comparison,omitempty"`
}

func classifyGap(score float64) (string, string) {
	for _, l := range levels {
		if score <= l.threshold {
			return l.name, l.indicator
		}
	}
	return "critical", "🔴"
}

// round1 rounds f to one decimal place, matching Python's round(f, 1).
func round1(f float64) float64 {
	return math.Round(f*10) / 10
}

func loadResults(path string) ([]TestResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var in inputFile
	if err := json.Unmarshal(data, &in); err != nil {
		return nil, err
	}
	if in.Tests == nil {
		return []TestResult{}, nil
	}
	return in.Tests, nil
}

func buildReport(sealed []TestResult, open []TestResult, hasOpen bool) Report {
	total := len(sealed)

	var rawFailures []TestResult
	for _, t := range sealed {
		if t.Status == "failed" {
			rawFailures = append(rawFailures, t)
		}
	}
	passed := total - len(rawFailures)

	var score float64
	if total > 0 {
		score = round1(float64(len(rawFailures)) / float64(total) * 100)
	}
	level, _ := classifyGap(score)

	failures := make([]Failure, 0, len(rawFailures))
	for _, f := range rawFailures {
		cat := f.Category
		if cat == "" {
			cat = "unknown"
		}
		failures = append(failures, Failure{
			TestName: f.Name,
			Category: cat,
			Expected: f.Expected,
			Actual:   f.Actual,
			Message:  f.Message,
		})
	}

	report := Report{
		SpecVersion: specVersion,
		Report: reportSummary{
			ShadowScore: score,
			Level:    level,
		},
		SealedTests: testStats{
			Total:  total,
			Passed: passed,
			Failed: len(rawFailures),
		},
		Failures: failures,
	}

	if hasOpen {
		oTotal := len(open)
		oFailed := 0
		for _, t := range open {
			if t.Status == "failed" {
				oFailed++
			}
		}
		report.OpenTests = &testStats{
			Total:  oTotal,
			Passed: oTotal - oFailed,
			Failed: oFailed,
		}

		comparison := make(map[string]CategoryComparison, len(categories))
		for _, cat := range categories {
			sCount, oCount := 0, 0
			for _, t := range sealed {
				if t.Category == cat {
					sCount++
				}
			}
			for _, t := range open {
				if t.Category == cat {
					oCount++
				}
			}
			comparison[cat] = CategoryComparison{
				Sealed: sCount,
				Open:   oCount,
				Delta:  sCount - oCount,
			}
		}
		report.CoverageComparison = comparison
	}

	return report
}

func main() {
	sealedPath := flag.String("sealed", "", "Path to sealed test results JSON (required)")
	openPath := flag.String("open", "", "Path to open test results JSON (optional)")
	format := flag.String("format", "json", "Output format: json or summary")

	var thresholdVal float64
	var hasThreshold bool
	flag.Func("threshold", "Exit with code 1 if Shadow Score exceeds this threshold", func(s string) error {
		v, err := strconv.ParseFloat(s, 64)
		if err != nil {
			return fmt.Errorf("threshold must be a number: %w", err)
		}
		thresholdVal = v
		hasThreshold = true
		return nil
	})

	flag.Parse()

	if *sealedPath == "" {
		fmt.Fprintln(os.Stderr, "Error: --sealed is required")
		flag.Usage()
		os.Exit(2)
	}

	sealed, err := loadResults(*sealedPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading sealed results: %v\n", err)
		os.Exit(2)
	}

	hasOpen := *openPath != ""
	var open []TestResult
	if hasOpen {
		open, err = loadResults(*openPath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error loading open results: %v\n", err)
			os.Exit(2)
		}
	}

	report := buildReport(sealed, open, hasOpen)

	if *format == "summary" {
		score := report.Report.ShadowScore
		level := report.Report.Level
		_, indicator := classifyGap(score)
		fmt.Printf("Shadow Score: %.1f%% %s (%s)\n", score, indicator, level)
		fmt.Printf("Sealed: %d/%d passed\n", report.SealedTests.Passed, report.SealedTests.Total)
		if report.OpenTests != nil {
			fmt.Printf("Open:   %d/%d passed\n", report.OpenTests.Passed, report.OpenTests.Total)
		}
		if len(report.Failures) > 0 {
			fmt.Printf("\nFailures (%d):\n", len(report.Failures))
			for _, f := range report.Failures {
				fmt.Printf("  ❌ %s: %s\n", f.TestName, f.Message)
			}
		}
	} else {
		out, err := json.MarshalIndent(report, "", "  ")
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error marshaling output: %v\n", err)
			os.Exit(2)
		}
		fmt.Println(string(out))
	}

	if hasThreshold && report.Report.ShadowScore > thresholdVal {
		os.Exit(1)
	}
}
