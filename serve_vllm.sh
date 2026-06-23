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

# Kill any stale VLLM::EngineCore processes left from a previous run
stale=$(nvidia-smi --query-compute-apps=pid,name --format=csv,noheader 2>/dev/null \
        | awk -F',' '/VLLM::EngineCore/{print $1}' | tr -d ' ')
if [ -n "$stale" ]; then
  echo "Killing stale EngineCore PID(s): $stale"
  kill $stale 2>/dev/null || true
  sleep 2
fi

# On Ctrl+C / SIGTERM, kill the whole process group so EngineCore doesn't linger
cleanup() { kill -- -$$ 2>/dev/null || true; }
trap cleanup INT TERM

"$VLLM" serve "$MODEL" \
  --download-dir "$DOWNLOAD_DIR" \
  --dtype float16 \
  --max-model-len "$MAX_LEN" \
  --port "$PORT" \
  --served-model-name "qwen3.6-27b-awq" \
  --gpu-memory-utilization 0.92 \
  --max-num-seqs 64 &

VLLM_PID=$!
wait $VLLM_PID
