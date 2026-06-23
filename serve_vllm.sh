#!/usr/bin/env bash
# Usage: ./serve_vllm.sh [MODEL_HF_ID]
# Default model: cyankiwi/Qwen3.6-27B-AWQ-INT4

set -euo pipefail

VLLM="/home/nullkuhl/vllm-env/bin/vllm"
MODEL="${1:-cyankiwi/Qwen3.6-27B-AWQ-INT4}"
DOWNLOAD_DIR="/home/nullkuhl/models"
PORT="${PORT:-8000}"
MAX_LEN="${MAX_LEN:-65536}"

echo "Starting vLLM server"
echo "  Model:        $MODEL"
echo "  Download dir: $DOWNLOAD_DIR"
echo "  Port:         $PORT"
echo "  Max len:      $MAX_LEN"
echo ""

exec "$VLLM" serve "$MODEL" \
  --download-dir "$DOWNLOAD_DIR" \
  --dtype float16 \
  --max-model-len "$MAX_LEN" \
  --port "$PORT" \
  --served-model-name "qwen3.6-27b-awq" \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs 64
