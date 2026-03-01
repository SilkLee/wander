#!/bin/bash
# Test Agent workflow with Qwen2.5-1.5B-Instruct model
# Run this script on EC2 after deploying the model upgrade

set -e

echo "=== Agent Workflow Test (Qwen2.5-1.5B-Instruct) ==="
echo ""
echo "Testing with database connection timeout log..."
echo ""

# Test payload with realistic error log
RESPONSE=$(curl -X POST http://localhost:8002/workflows/analyze-log \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "ERROR: Connection timeout at database.py:142\nTraceback (most recent call last):\n  File \"database.py\", line 142, in connect\n    conn = psycopg2.connect(host=DB_HOST, port=5432, timeout=30)\n  File \"/usr/lib/python3.9/site-packages/psycopg2/__init__.py\", line 122, in connect\n    conn = _connect(dsn, connection_factory=connection_factory, **kwasync)\npsycopg2.OperationalError: timeout expired (30 seconds)\nCould not establish connection to PostgreSQL database at 10.0.1.50:5432",
    "log_type": "application"
  }' \
  --max-time 180 \
  -w "\n\nHTTP Status: %{http_code}\nTotal Time: %{time_total}s\n" \
  -s)

echo "$RESPONSE"
echo ""

# Parse and validate response
ROOT_CAUSE=$(echo "$RESPONSE" | grep -o '"root_cause":"[^"]*"' | head -1)
SEVERITY=$(echo "$RESPONSE" | grep -o '"severity":"[^"]*"' | head -1)
CONFIDENCE=$(echo "$RESPONSE" | grep -o '"confidence":[0-9.]*' | head -1)

echo "=== Validation ==="
echo ""

# Check for gibberish output (old GPT-2 behavior)
if echo "$ROOT_CAUSE" | grep -q "final answer to the original input question"; then
    echo "❌ FAILED: Output contains GPT-2 prompt echo"
    echo "   This means the model is still using gpt2 instead of Qwen"
    echo ""
    echo "Debug steps:"
    echo "1. Check model service logs: docker logs workflowai-model --tail 100"
    echo "2. Verify environment: docker exec workflowai-model env | grep MODEL_NAME"
    echo "3. Check config: docker exec workflowai-model cat /app/app/config.py | grep model_name"
    exit 1
fi

# Check if root_cause is meaningful
if [ -z "$ROOT_CAUSE" ] || [ "$ROOT_CAUSE" = '"root_cause":""' ]; then
    echo "❌ FAILED: No root_cause found in response"
    exit 1
else
    echo "✓ root_cause field present"
    echo "  $ROOT_CAUSE"
fi

# Check severity
if [ -z "$SEVERITY" ]; then
    echo "⚠ WARNING: No severity found in response"
else
    echo "✓ severity field present"
    echo "  $SEVERITY"
    
    # Database timeout should be high/critical severity
    if echo "$SEVERITY" | grep -qE '(high|critical)'; then
        echo "  ✓ Severity correctly classified (expected high/critical for DB timeout)"
    else
        echo "  ⚠ Severity may be underestimated (expected high/critical)"
    fi
fi

# Check confidence
if [ -z "$CONFIDENCE" ]; then
    echo "⚠ WARNING: No confidence found in response"
else
    echo "✓ confidence field present"
    echo "  $CONFIDENCE"
    
    # Extract numeric value
    CONF_VALUE=$(echo "$CONFIDENCE" | grep -o '[0-9.]*')
    if [ -n "$CONF_VALUE" ]; then
        # Check if confidence >= 0.7 (using bc for float comparison)
        if command -v bc &> /dev/null; then
            if (( $(echo "$CONF_VALUE >= 0.7" | bc -l) )); then
                echo "  ✓ Confidence >= 0.7 (good quality)"
            else
                echo "  ⚠ Confidence < 0.7 (may need review)"
            fi
        fi
    fi
fi

# Check if suggested_fixes exist
FIXES=$(echo "$RESPONSE" | grep -o '"suggested_fixes":\[[^]]*\]' | head -1)
if [ -z "$FIXES" ] || [ "$FIXES" = '"suggested_fixes":[]' ]; then
    echo "⚠ WARNING: No suggested_fixes in response"
else
    echo "✓ suggested_fixes field present"
    # Count number of fixes
    FIX_COUNT=$(echo "$FIXES" | grep -o ',' | wc -l)
    FIX_COUNT=$((FIX_COUNT + 1))
    echo "  Found $FIX_COUNT suggested fix(es)"
fi

echo ""
echo "=== Summary ==="

# Overall assessment
if echo "$ROOT_CAUSE" | grep -q "final answer to the original input question"; then
    echo "Status: ❌ FAILED (still using GPT-2)"
    exit 1
elif [ -n "$ROOT_CAUSE" ] && [ -n "$SEVERITY" ] && [ -n "$CONFIDENCE" ]; then
    echo "Status: ✅ PASSED (Qwen model producing structured output)"
    echo ""
    echo "Day 10 Agent workflow validation: SUCCESS"
    echo "- Model: Qwen2.5-1.5B-Instruct"
    echo "- Output: Structured analysis (not prompt echo)"
    echo "- Quality: Meets Day 10 acceptance criteria"
    exit 0
else
    echo "Status: ⚠ PARTIAL (missing some fields)"
    exit 1
fi
