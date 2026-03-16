package parser

import (
	"regexp"
	"strconv"
	"strings"
)

// LogType represents the type of log
type LogType string

const (
	LogTypeBuild  LogType = "build"
	LogTypeDeploy LogType = "deploy"
	LogTypeTest   LogType = "test"
)

// FailureSignal represents extracted failure information
type FailureSignal struct {
	Type         LogType  `json:"type"`
	ErrorMessage string   `json:"error_message"`
	StackTrace   string   `json:"stack_trace,omitempty"`
	FailedStep   string   `json:"failed_step,omitempty"`
	ExitCode     int      `json:"exit_code,omitempty"`
	Keywords     []string `json:"keywords"`
	LineNumber   int      `json:"line_number,omitempty"`
}

// ParseLog extracts failure signals from CI/CD logs
func ParseLog(content string, logType LogType) *FailureSignal {
	signal := &FailureSignal{
		Type:     logType,
		Keywords: []string{},
	}

	lines := strings.Split(content, "\n")

	// Pre-compiled error patterns (avoid recompiling inside loops)
var errorPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)error:?\s*(.+)`),
	regexp.MustCompile(`(?i)exception:?\s*(.+)`),
	regexp.MustCompile(`(?i)fatal:?\s*(.+)`),
	regexp.MustCompile(`(?i)failed:?\s*(.+)`),
	regexp.MustCompile(`(?i)panic:?\s*(.+)`),
}

var exitCodeRe = regexp.MustCompile(`exit code:?\s*(\d+)`)

	var errorLines []string
	var stackTraceLines []string
	inStackTrace := false

	for i, line := range lines {
		trimmedLine := strings.TrimSpace(line)

		// Skip empty lines
		if trimmedLine == "" {
			continue
		}

		// Check for error patterns
		for _, re := range errorPatterns {
			if matches := re.FindStringSubmatch(trimmedLine); len(matches) > 1 {
				errorLines = append(errorLines, matches[1])
				signal.LineNumber = i + 1
				inStackTrace = true

				// Extract keywords
				keywords := extractKeywords(trimmedLine)
				signal.Keywords = append(signal.Keywords, keywords...)
				break
			}
		}

		// Collect stack trace (lines following error)
		if inStackTrace {
			// Stack trace indicators
			if strings.Contains(trimmedLine, "at ") ||
				strings.HasPrefix(trimmedLine, "  ") ||
				strings.Contains(trimmedLine, ".go:") ||
				strings.Contains(trimmedLine, ".py:") ||
				strings.Contains(trimmedLine, ".java:") {
				stackTraceLines = append(stackTraceLines, trimmedLine)
			} else if len(stackTraceLines) > 0 {
				// End of stack trace
				inStackTrace = false
			}
		}

		// Extract failed step (common CI patterns)
		if strings.Contains(trimmedLine, "Step") && strings.Contains(trimmedLine, "failed") {
			signal.FailedStep = trimmedLine
		}

		// Extract exit code
		if matches := exitCodeRe.FindStringSubmatch(trimmedLine); len(matches) > 1 {
			signal.ExitCode = parseExitCode(matches[1])
		}
	}

	// Combine error messages
	if len(errorLines) > 0 {
		signal.ErrorMessage = strings.Join(errorLines, "; ")
	}

	// Combine stack trace
	if len(stackTraceLines) > 0 {
		signal.StackTrace = strings.Join(stackTraceLines, "\n")
	}

	// Deduplicate keywords
	signal.Keywords = uniqueStrings(signal.Keywords)

	return signal
}

// extractKeywords extracts meaningful keywords from error line
func extractKeywords(line string) []string {
	var keywords []string

	// Common error keywords
	patterns := []string{
		"NullPointerException",
		"OutOfMemoryError",
		"ConnectionRefused",
		"Timeout",
		"Permission denied",
		"No such file",
		"Syntax error",
		"Import error",
		"Module not found",
		"Compilation failed",
		"Test failed",
		"Assertion failed",
		"Segmentation fault",
		"Stack overflow",
	}

	lowerLine := strings.ToLower(line)
	for _, keyword := range patterns {
		if strings.Contains(lowerLine, strings.ToLower(keyword)) {
			keywords = append(keywords, keyword)
		}
	}

	return keywords
}

// parseExitCode parses exit code from string
func parseExitCode(s string) int {
	code, err := strconv.Atoi(s)
	if err != nil {
		return 1
	}
	return code
}

// uniqueStrings returns unique strings from slice
func uniqueStrings(input []string) []string {
	seen := make(map[string]bool)
	var result []string

	for _, str := range input {
		if !seen[str] {
			seen[str] = true
			result = append(result, str)
		}
	}

	return result
}
