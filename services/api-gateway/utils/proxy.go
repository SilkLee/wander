package utils

import (
	"io"
	"net"
	"net/http"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// sharedClient is a package-level HTTP client with connection pooling.
// Reused across all proxy requests to avoid per-request TCP handshake overhead.
var sharedClient = &http.Client{
	Transport: &http.Transport{
		DialContext: (&net.Dialer{
			Timeout:   10 * time.Second,
			KeepAlive: 30 * time.Second,
		}).DialContext,
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 20,
		IdleConnTimeout:     90 * time.Second,
		TLSHandshakeTimeout: 10 * time.Second,
	},
	Timeout: 30 * time.Second,
}

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

		// Send request using shared pooled client
		resp, err := sharedClient.Do(req)
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

// ProxyToExactURL creates a handler that proxies requests to an exact URL without appending the request path.
// Use this when the gateway route path differs from the downstream service path.
func ProxyToExactURL(targetURL string) gin.HandlerFunc {
	return func(c *gin.Context) {
		url := targetURL
		if c.Request.URL.RawQuery != "" {
			url += "?" + c.Request.URL.RawQuery
		}

		req, err := http.NewRequest(c.Request.Method, url, c.Request.Body)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to create proxy request",
			})
			return
		}

		for key, values := range c.Request.Header {
			for _, value := range values {
				req.Header.Add(key, value)
			}
		}

		if userID, exists := c.Get("userID"); exists {
			req.Header.Set("X-User-ID", userID.(string))
		}
		if username, exists := c.Get("username"); exists {
			req.Header.Set("X-Username", username.(string))
		}

		resp, err := sharedClient.Do(req)
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{
				"error": "Failed to reach downstream service",
			})
			return
		}
		defer resp.Body.Close()

		for key, values := range resp.Header {
			for _, value := range values {
				c.Writer.Header().Add(key, value)
			}
		}

		c.Status(resp.StatusCode)
		io.Copy(c.Writer, resp.Body)
	}
}
