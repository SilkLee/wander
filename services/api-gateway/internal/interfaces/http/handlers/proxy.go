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
