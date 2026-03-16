package handlers

import (
	"workflow-ai/gateway/config"
	"workflow-ai/gateway/utils"

	"github.com/gin-gonic/gin"
)

// ProxyHandler handles proxying requests to downstream services
type ProxyHandler struct {
	config *config.Config
}

// NewProxyHandler creates a new ProxyHandler
func NewProxyHandler(cfg *config.Config) *ProxyHandler {
	return &ProxyHandler{
		config: cfg,
	}
}

// Ingestion Service endpoints
func (h *ProxyHandler) ProxyIngestion(c *gin.Context) {
	utils.ProxyToService(h.config.IngestionServiceURL)(c)
}

func (h *ProxyHandler) ProxyIngestionHealth(c *gin.Context) {
	utils.ProxyToService(h.config.IngestionServiceURL + "/health")(c)
}

// Indexing Service endpoints
func (h *ProxyHandler) ProxyIndex(c *gin.Context) {
	utils.ProxyToService(h.config.IndexingServiceURL)(c)
}

func (h *ProxyHandler) ProxyIndexBatch(c *gin.Context) {
	utils.ProxyToService(h.config.IndexingServiceURL + "/index/batch")(c)
}

func (h *ProxyHandler) ProxySearch(c *gin.Context) {
	utils.ProxyToService(h.config.IndexingServiceURL)(c)
}

func (h *ProxyHandler) ProxyStats(c *gin.Context) {
	utils.ProxyToService(h.config.IndexingServiceURL)(c)
}

// Agent Orchestrator endpoints
func (h *ProxyHandler) ProxyExecute(c *gin.Context) {
	utils.ProxyToService(h.config.AgentServiceURL)(c)
}

func (h *ProxyHandler) ProxyExecuteGet(c *gin.Context) {
	utils.ProxyToService(h.config.AgentServiceURL + "/execute")(c)
}

// Model Service endpoints
func (h *ProxyHandler) ProxyGenerate(c *gin.Context) {
	utils.ProxyToService(h.config.ModelServiceURL)(c)
}

func (h *ProxyHandler) ProxyModelInfo(c *gin.Context) {
	utils.ProxyToService(h.config.ModelServiceURL + "/model/info")(c)
}

// Metrics Service endpoints
func (h *ProxyHandler) ProxyMetrics(c *gin.Context) {
	utils.ProxyToService(h.config.MetricsServiceURL)(c)
}

func (h *ProxyHandler) ProxyMetricsHealth(c *gin.Context) {
	utils.ProxyToService(h.config.MetricsServiceURL + "/health")(c)
}

// Workflow endpoints (proxy to Agent Orchestrator with exact URL rewrite)
func (h *ProxyHandler) ProxyWorkflowAnalyzeLog(c *gin.Context) {
	utils.ProxyToExactURL(h.config.AgentServiceURL + "/workflows/analyze-log")(c)
}

func (h *ProxyHandler) ProxyWorkflowAnalyzeLogStream(c *gin.Context) {
	utils.ProxyToExactURL(h.config.AgentServiceURL + "/workflows/analyze-log/stream")(c)
}

func (h *ProxyHandler) ProxyWorkflowExecute(c *gin.Context) {
	utils.ProxyToExactURL(h.config.AgentServiceURL + "/workflows/execute")(c)
}

func (h *ProxyHandler) ProxyWorkflowTypes(c *gin.Context) {
	utils.ProxyToExactURL(h.config.AgentServiceURL + "/workflows/types")(c)
}

// Public Metrics endpoints (proxy to Metrics Service with path rewrite)
// Handles /api/metrics/*path -> http://metrics:8005/metrics/*path
func (h *ProxyHandler) ProxyMetricsDORA(c *gin.Context) {
	utils.ProxyToExactURL(h.config.MetricsServiceURL + "/metrics/dora")(c)
}

func (h *ProxyHandler) ProxyMetricsDeploymentEvent(c *gin.Context) {
	utils.ProxyToExactURL(h.config.MetricsServiceURL + "/metrics/events/deployment")(c)
}

func (h *ProxyHandler) ProxyMetricsChangeEvent(c *gin.Context) {
	utils.ProxyToExactURL(h.config.MetricsServiceURL + "/metrics/events/change")(c)
}

func (h *ProxyHandler) ProxyMetricsIncidentEvent(c *gin.Context) {
	utils.ProxyToExactURL(h.config.MetricsServiceURL + "/metrics/events/incident")(c)
}

func (h *ProxyHandler) ProxyMetricsEvents(c *gin.Context) {
	utils.ProxyToExactURL(h.config.MetricsServiceURL + "/metrics/events")(c)
}
