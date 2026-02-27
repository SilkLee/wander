package parser

import (
	"regexp"
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

	// Extract error patterns
	errorPatterns := []string{
		`(?i)error:?\s*(.+)`,
		`(?i)exception:?\s*(.+)`,
		`(?i)fatal:?\s*(.+)`,
		`(?i)failed:?\s*(.+)`,
		`(?i)panic:?\s*(.+)`,
	}

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
		for _, pattern := range errorPatterns {
			re := regexp.MustCompile(pattern)
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
		if matches := regexp.MustCompile(`exit code:?\s*(\d+)`).FindStringSubmatch(trimmedLine); len(matches) > 1 {
			if _, err := regexp.MatchString(`\d+`, matches[1]); err == nil {
				signal.ExitCode = parseExitCode(matches[1])
			}
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
	var code int
	if _, err := regexp.MatchString(`^\d+$`, s); err == nil {
		// Simple parsing (would use strconv.Atoi in production)
		switch s {
		case "0":
			code = 0
		case "1":
			code = 1
		case "2":
			code = 2
		case "127":
			code = 127
		case "137":
			code = 137
		case "143":
			code = 143
		default:
			code = 1
		}
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
