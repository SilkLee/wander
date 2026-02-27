#!/usr/bin/env bash
#
# Quick Local Test for Model Service
# Tests model loading from local directory
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Model Service - Local Test${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if model directory exists
MODEL_DIR="C:/develop/Qwen2.5-7B-Instruct"

if [ ! -d "$MODEL_DIR" ]; then
    echo -e "${RED}✗ Model directory not found: $MODEL_DIR${NC}"
    echo -e "${YELLOW}Please download the model first using the provided PowerShell script${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Model directory found: $MODEL_DIR"

# Check critical files
FILES=("config.json" "model-00001-of-00004.safetensors" "tokenizer.json")
for file in "${FILES[@]}"; do
    if [ -f "$MODEL_DIR/$file" ]; then
        echo -e "${GREEN}✓${NC} $file exists"
    else
        echo -e "${RED}✗${NC} $file missing"
        exit 1
    fi
done

echo -e "\n${BLUE}Model files validated${NC}\n"

# Setup Python environment
echo -e "${YELLOW}Setting up Python environment...${NC}"
cd C:/develop/workflow-ai/services/model-service

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python -m venv .venv
fi

# Activate virtual environment
source .venv/Scripts/activate || source .venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -e .

# Set environment variables for local testing
export PORT=8004
export MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
export LOCAL_MODEL_PATH="$MODEL_DIR"
export DEVICE=cpu
export MAX_MODEL_LEN=4096
export DEBUG=true

echo -e "\n${BLUE}Environment configured:${NC}"
echo "  MODEL_NAME: $MODEL_NAME"
echo "  LOCAL_MODEL_PATH: $LOCAL_MODEL_PATH"
echo "  DEVICE: $DEVICE"
echo ""

# Test model loading
echo -e "${YELLOW}Testing model loading (this may take 1-2 minutes)...${NC}\n"

python -c "
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'app'))

from app.config import settings
from app.services.inference import InferenceService

print(f'Loading model from: {settings.local_model_path}')
print(f'Device: {settings.device}')

try:
    service = InferenceService()
    print('\\n✓ Model loaded successfully!')
    
    # Get model info
    info = service.get_model_info()
    print(f'  Name: {info[\"name\"]}')
    print(f'  Path: {info[\"path\"]}')
    print(f'  Is Local: {info[\"is_local\"]}')
    print(f'  Device: {info[\"device\"]}')
    
    # Test generation
    print('\\nTesting text generation...')
    text, tokens, reason = service.generate(
        prompt='Hello, how are you?',
        max_tokens=20,
        temperature=0.7
    )
    print(f'  Prompt: Hello, how are you?')
    print(f'  Generated: {text}')
    print(f'  Tokens: {tokens}')
    print(f'  Finish Reason: {reason}')
    
    print('\\n✓ All tests passed!')
    sys.exit(0)
    
except Exception as e:
    print(f'\\n✗ Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Local test completed successfully${NC}"
    echo -e "${GREEN}========================================${NC}\n"
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. Build Docker image: cd C:/develop/workflow-ai && docker compose build model-service"
    echo "2. Update docker-compose.yml to uncomment model volume mount"
    echo "3. Start service: docker compose up -d model-service"
    echo "4. Run E2E tests: bash test-model-e2e.sh"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}✗ Local test failed${NC}"
    echo -e "${RED}========================================${NC}\n"
    exit 1
fi
