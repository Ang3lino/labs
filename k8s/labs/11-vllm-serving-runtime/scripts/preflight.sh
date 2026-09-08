#!/usr/bin/env bash
# Run this BEFORE applying 01-vllm-cpu.yaml.
#
# The published vLLM CPU images are compiled with AVX512. On a CPU without it the
# container dies instantly with exit code 132 (SIGILL, illegal instruction) and a
# log that stops right after "Automatically detected platform cpu" - no Python
# traceback, no error message. Thirty seconds here saves an hour of confusion.
set -uo pipefail

echo "== CPU preflight for vLLM CPU build =="

flags=$(grep -m1 '^flags' /proc/cpuinfo 2>/dev/null || echo "")
model=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2- | sed 's/^ *//')
[ -n "$model" ] && echo "cpu: $model"

has() { echo "$flags" | grep -qw "$1"; }

if has avx512f; then
  echo "  AVX512  present  -> vLLM CPU image should run"
  exit 0
fi

echo "  AVX512  MISSING"
has avx2 && echo "  AVX2    present (not sufficient for the prebuilt CPU image)"
cat <<'MSG'

The prebuilt vLLM CPU image will crash with exit 132 (SIGILL) on this machine.

Options:
  1. Run Parts A and C only. Part A (criteria) needs no cluster at all, and it is
     the part that actually decides the runtime.
  2. Build vLLM from source for your CPU:
     https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html
  3. Run Part B on any AVX512 host - most server-class Xeons, and the GPU nodes
     you are evaluating for the real deployment.

Note this is a limitation of the CPU BUILD, not of vLLM. GPU images are unaffected.
MSG
exit 1