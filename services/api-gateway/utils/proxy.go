package utils

import (
	"io"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// ProxyToService creates a handler function that proxies requests to a downstream service
func ProxyToService(targetURL string) gin.HandlerFunc {
	return func(c *gin.Context) {
		// Build target URL with path
		url := targetURL
		if !strings.HasSuffix(targetURL, c.Request.URL.Path) {
			url = targetURL + c.Request.URL.Path
		}
		if c.Request.URL.RawQuery != "" {
			url += "?" + c.Request.URL.RawQuery
		}

		// Create new request
		req, err := http.NewRequest(c.Request.Method, url, c.Request.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to create proxy request",
			})
			return
		}

		// Copy headers
		for key, values := range c.Request.Header {
			for _, value := range values {
				req.Header.Add(key, value)
			}
		}

		// Add user context if available
		if userID, exists := c.Get("userID"); exists {
			req.Header.Set("X-User-ID", userID.(string))
		}
		if username, exists := c.Get("username"); exists {
			req.Header.Set("X-Username", username.(string))
		}

		// Send request
		client := &http.Client{}
		resp, err := client.Do(req)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{
				"error": "Failed to reach downstream service",
			})
			return
		}
		defer resp.Body.Close()

		// Copy response headers
		for key, values := range resp.Header {
			for _, value := range values {
				c.Writer.Header().Add(key, value)
			}
		}

		// Copy status code and body
		c.Status(resp.StatusCode)
		io.Copy(c.Writer, resp.Body)
	}
}
