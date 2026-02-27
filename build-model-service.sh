#!/usr/bin/env bash
#
# Day 7 - Model Service Build Script
# Alternative to PowerShell script for Git Bash users
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Day 7: Model Service - Build & Deploy${NC}"
echo -e "${BLUE}========================================${NC}\n"

cd /c/develop/workflow-ai || cd C:/develop/workflow-ai

echo -e "${YELLOW}[Step 1/3] Building Model Service image...${NC}"
echo -e "${CYAN}Using gpt2 model (~500MB, fast startup)${NC}\n"

# Try docker command
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker command not found${NC}"
    echo -e "${YELLOW}Please run test-model-build.ps1 in PowerShell instead${NC}"
    exit 1
fi

# Build
docker compose build model-service
echo -e "\n${GREEN}✓ Image built successfully${NC}"

# Start
echo -e "\n${YELLOW}[Step 2/3] Starting container...${NC}"
docker compose up -d model-service
echo -e "${GREEN}✓ Container started${NC}"

# Wait for health
echo -e "\n${YELLOW}[Step 3/3] Waiting for service (max 5 minutes)...${NC}"

for i in {1..30}; do
    echo -e "${CYAN}  Attempt $i/30...${NC}" 
    
    if curl -s http://localhost:8004/health | grep -q '"model_loaded":true'; then
        echo -e "${GREEN}✓ Model loaded!${NC}\n"
        
        # Show health status
        echo -e "${BLUE}Service Status:${NC}"
        curl -s http://localhost:8004/health | jq '.'
        
        echo -e "\n${GREEN}========================================${NC}"
        echo -e "${GREEN}✓ Model Service is ready!${NC}"
        echo -e "${GREEN}========================================${NC}\n"
        
        echo -e "${CYAN}Test with:${NC}"
        echo -e "  bash test-model-e2e.sh"
        echo -e "\n${CYAN}Or manually:${NC}"
        echo -e "  curl http://localhost:8004/health"
        echo -e '  curl -X POST http://localhost:8004/generate \\'
        echo -e '    -H "Content-Type: application/json" \\'
        echo -e '    -d '"'"'{"prompt":"Hello!","max_tokens":20}'"'"
        echo ""
        exit 0
    fi
    
    sleep 10
done

echo -e "${RED}✗ Service did not become healthy within 5 minutes${NC}"
echo -e "${YELLOW}Check logs: docker compose logs model-service${NC}"
exit 1
