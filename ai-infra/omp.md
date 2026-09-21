# OMP Model Roles — Bedrock Research Notes

Research for `omp config set modelRoles`, evaluating Chinese-origin models (DeepSeek, Moonshot AI/Kimi, Qwen, Z.AI/GLM, MiniMax) and Amazon Nova against the currently configured Anthropic models, for the three omp roles: `default`, `smol`, `slow`.

Previous config (pre-fix, what threw the Bedrock 400):

```json
{
  "default": "amazon-bedrock/global.moonshotai.kimi-k3",
  "smol":    "amazon-bedrock/zai.glm-4.7-flash",
  "slow":    "amazon-bedrock/zai.glm-5"
}
```

**Adopted config** (verified against omp's live model catalog and a real tool-call turn on each role — see §0):

```json
{
  "default": "amazon-bedrock/zai.glm-5",
  "smol":    "amazon-bedrock/minimax.minimax-m2.5",
  "slow":    "amazon-bedrock/moonshotai.kimi-k2.5"
}
```

**Sources:** `docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html` (catalog + model IDs + capability tables) and `aws.amazon.com/bedrock/pricing/` (all $ figures), fetched live. Date of research: 2026-09-21. Catalog verified live via `omp models ls amazon-bedrock --json`.

**Important caveat:** Performance rankings below are `[INFERENCE]`, not benchmark results. AWS's model-card pages publish zero benchmark scores, and Claude Sonnet 5 / Opus 5 / GLM 5 are all too recent for third-party evals to exist. Rankings are derived from: (1) each model card's own positioning language, (2) spec parity (context window, max output tokens) vs. the Claude model in that role, (3) directional reputation of that model family's prior generation on public benchmarks. Price figures are hard data pulled directly from the AWS pricing page and are not inference.

---
## 0. Errata (2026-09-21 follow-up) — bugs found applying this doc

Applying the config below hit `Bedrock HTTP 400: toolConfig.tools.N.member.toolSpec.description ... length >= 1`. Root-caused and fixed.

**Bug 1 — `inlineToolDescriptors=auto` strips tool descriptions for non-Gemini Bedrock models too.** Confirmed by inspecting the raw failing request (`~/.omp/logs/http-400-requests/`): every one of the ~12 `toolSpec.description` fields was sent as `""` to `zai.glm-5` on the Bedrock Converse API. `inlineToolDescriptors` (default `auto`) is documented to enable description-stripping "for Gemini models" only and disable it otherwise, but it also fired for this GLM-5 call (likely because GLM-5 was invoked with `additionalModelRequestFields.thinking`, matching whatever heuristic `auto` actually uses instead of a strict Gemini-provider check). Anthropic models never hit this because Claude tool calls on Bedrock don't route through the generic `toolConfig` schema the same way. **Fix:** `omp config set inlineToolDescriptors off` (done; also updated `omp` 18.2.5 → 18.2.8, no changelog evidence it alone fixes this, so keep the explicit override). Verified: identical GLM-5 + tools + thinking request now completes.

**Bug 2 — Removed non-existent models.** Kimi K3, GLM 4.7, Nova Premier (EOL), DeepSeek R1 (not on Bedrock), and Nova Pro (EOL) have been removed from all tables. Only models verified via `omp models ls amazon-bedrock --json` are included.

**Revised picks (real catalog):** `default`→GLM-5 (best all-around reliability/cost among models that actually exist), `smol`→MiniMax M2.5 (cheap, punches above its weight, reasoning-capable), `slow`→Kimi K2.5 (long-context, low-hallucination, strongest genuine "thorough analysis" fit). All three confirmed via `omp -p --model <selector> ...` to resolve to themselves (no silent fallback) and to complete a real tool-calling turn.


## 1. Bedrock catalog — Chinese-origin providers (verified)

| Provider | Models available on Bedrock (verified 2026-09-21) |
|---|---|
| DeepSeek | DeepSeek V3.2, DeepSeek V3.1 |
| Moonshot AI (Kimi) | Kimi K2.5, Kimi K2 Thinking |
| Qwen (Alibaba) | Qwen3 Coder 480B A35B, Qwen3 Coder 30B A3B, Qwen3 Coder Next, Qwen3 Next 80B A3B, Qwen3 235B A22B 2507, Qwen3 32B, Qwen3 VL 235B A22B |
| Z.AI (GLM) | GLM 5, GLM 4.7 Flash |
| MiniMax | MiniMax M2.5, MiniMax M2.1, MiniMax M2 |

Amazon's own models: Nova Micro, Nova Lite, Nova 2 Lite. Note: Nova Premier, Nova Pro are not in the live catalog as of 2026-09-21.

---

## 2. Master pricing table

US East (N. Virginia/Ohio/Oregon), Standard on-demand tier, USD per 1M tokens. "Not supported" = the model's Bedrock capability table has no caching/batch section at all (grounded per model card). "Not published" = feature is listed as supported but AWS's pricing page shows no rate for it.

| Model | omp argument | Input | Output | Cache Write | Cache Read | Batch | Priority (+75%) | Flex (−50%) |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5 | `amazon-bedrock/us.anthropic.claude-opus-5` | $5.00 | $25.00 | ✓ | ✓ | ✓ | ✗ | ✗ |
| Claude Sonnet 5 | `amazon-bedrock/us.anthropic.claude-sonnet-5` | $2.00 | $10.00 | ✓ | ✓ | ✗ | ✗ | ✗ |
| Claude Haiku 4.5 | `amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0` | $1.00 | $5.00 | ✓ | ✓ | ✓ | ✗ | ✗ |
| Nova Lite | `amazon-bedrock/us.amazon.nova-lite-v1:0` | $0.06 | $0.24 | ✗ | ✗ | ✗ | not verified | not verified |
| Nova Micro | `amazon-bedrock/us.amazon.nova-micro-v1:0` | $0.035 | $0.14 | ✗ | ✗ | ✗ | not verified | not verified |
| GLM 5 | `amazon-bedrock/zai.glm-5` | $1.00 | $3.20 | ✗ | ✗ | ✓ | ✓ | ✓ |
| Qwen3 Coder 480B A35B | `amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0` | $0.45 | $1.80 | ✗ | ✗ | ✓ | ✓ | ✓ |
| Kimi K2 Thinking | `amazon-bedrock/moonshot.kimi-k2-thinking` | $0.60 | $2.50 | ✗ | ✗ | ✗ | ✓ | ✓ |
| Kimi K2.5 | `amazon-bedrock/moonshotai.kimi-k2.5` | $0.60 | $3.00 | ✗ | ✗ | ✗ | ✓ | ✓ |
| MiniMax M2.5 | `amazon-bedrock/minimax.minimax-m2.5` | $0.30 | $1.20 | ✗ | ✗ | ✗ | ✓ | ✓ |
| GLM 4.7 Flash | `amazon-bedrock/zai.glm-4.7-flash` | $0.07 | $0.40 | ✗ | ✗ | ✓ | ✓ | ✓ |
| DeepSeek V3.2 | `amazon-bedrock/deepseek.v3.2` | $0.55 | $2.19 | ✗ | ✗ | ✗ | ✓ | ✓ |

---

## 3. Rankings per role

### Column explanations

- **Performance Rank**: Inferred ordinal ranking (1 = best) based on positioning language, specs, and prior-generation benchmarks. Marked `[INFERENCE]` throughout.
- **Price Rank**: Ordinal ranking by output-token price (1 = cheapest). Output cost dominates in agentic/coding loops.
- **Value Score (pts/$)**: Calculated as **(N − rank + 1) ÷ output_price**, where N = number of models in that role's comparison set. This assigns points inversely to performance rank (best gets N points, worst gets 1 point), then normalizes by output price. Higher score = better value per dollar.
- **Value Rank**: Ordinal ranking by value score (1 = best value).

Example: If 5 models compete, the best performer gets 5 points, the worst gets 1 point. A model with rank 3 gets (5 - 3 + 1) = 3 points. If that model costs $3.20/1M output tokens, its value score = 3 ÷ 3.20 = 0.94 pts/$.

### `default` (competing with Claude Sonnet 5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Sonnet 5 | 1 | 3 ($10.00) | 4/10.00 = 0.40 | 3 |
| GLM 5 | 2 | 2 ($3.20) | 3/3.20 = 0.94 | 2 |
| Qwen3 Coder 480B | 3 | 1 ($1.80) | 2/1.80 = 1.11 | 1 |
| DeepSeek V3.2 | 4 | 4 ($2.19) | 1/2.19 = 0.46 | 4 |

### `smol` (competing with Claude Haiku 4.5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 6 ($5.00) | 6/5.00 = 1.20 | 5 |
| Kimi K2.5 | 2 | 5 ($3.00) | 5/3.00 = 1.67 | 4 |
| MiniMax M2.5 | 3 | 4 ($1.20) | 4/1.20 = 3.33 | 3 |
| GLM 4.7 Flash | 4 | 3 ($0.40) | 3/0.40 = 7.50 | 1 |
| Nova Lite | 5 | 2 ($0.24) | 2/0.24 = 8.33 | 2 |
| Nova Micro | 6 | 1 ($0.14) | 1/0.14 = 7.14 | 6 |

⚠️ In `smol`, performance and price are nearly independent (cheapest model ranks last on value), suggesting Nova Micro underperforms its price point.

### `slow` (competing with Claude Opus 5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Opus 5 | 1 | 3 ($25.00) | 3/25.00 = 0.12 | 3 |
| GLM 5 | 2 | 2 ($3.20) | 2/3.20 = 0.63 | 1 |
| Kimi K2 Thinking | 3 | 1 ($2.50) | 1/2.50 = 0.40 | 2 |

⚠️ Only 3 models in this tier. GLM 5 dominates value despite ranking #2 on performance, due to its 7.8× lower output cost vs Opus 5.

---

## 4. JSON exports — valid omp modelRoles configurations

### Performance (best → worst per role)

```json
{
  "performance": {
    "default": [
      { "rank": 1, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5" },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5" },
      { "rank": 3, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0" },
      { "rank": 4, "model": "DeepSeek V3.2", "omp_argument": "amazon-bedrock/deepseek.v3.2" }
    ],
    "smol": [
      { "rank": 1, "model": "Claude Haiku 4.5", "omp_argument": "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0" },
      { "rank": 2, "model": "Kimi K2.5", "omp_argument": "amazon-bedrock/moonshotai.kimi-k2.5" },
      { "rank": 3, "model": "MiniMax M2.5", "omp_argument": "amazon-bedrock/minimax.minimax-m2.5" },
      { "rank": 4, "model": "GLM 4.7 Flash", "omp_argument": "amazon-bedrock/zai.glm-4.7-flash" },
      { "rank": 5, "model": "Nova Lite", "omp_argument": "amazon-bedrock/us.amazon.nova-lite-v1:0" },
      { "rank": 6, "model": "Nova Micro", "omp_argument": "amazon-bedrock/us.amazon.nova-micro-v1:0" }
    ],
    "slow": [
      { "rank": 1, "model": "Claude Opus 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-opus-5" },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5" },
      { "rank": 3, "model": "Kimi K2 Thinking", "omp_argument": "amazon-bedrock/moonshot.kimi-k2-thinking" }
    ]
  }
}
```

### Price (cheapest → priciest per role)

```json
{
  "price": {
    "default": [
      { "rank": 1, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0", "output_price_usd_per_1m": 1.80 },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "output_price_usd_per_1m": 3.20 },
      { "rank": 3, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5", "output_price_usd_per_1m": 10.00 },
      { "rank": 4, "model": "DeepSeek V3.2", "omp_argument": "amazon-bedrock/deepseek.v3.2", "output_price_usd_per_1m": 2.19 }
    ],
    "smol": [
      { "rank": 1, "model": "Nova Micro", "omp_argument": "amazon-bedrock/us.amazon.nova-micro-v1:0", "output_price_usd_per_1m": 0.14 },
      { "rank": 2, "model": "Nova Lite", "omp_argument": "amazon-bedrock/us.amazon.nova-lite-v1:0", "output_price_usd_per_1m": 0.24 },
      { "rank": 3, "model": "GLM 4.7 Flash", "omp_argument": "amazon-bedrock/zai.glm-4.7-flash", "output_price_usd_per_1m": 0.40 },
      { "rank": 4, "model": "MiniMax M2.5", "omp_argument": "amazon-bedrock/minimax.minimax-m2.5", "output_price_usd_per_1m": 1.20 },
      { "rank": 5, "model": "Kimi K2.5", "omp_argument": "amazon-bedrock/moonshotai.kimi-k2.5", "output_price_usd_per_1m": 3.00 },
      { "rank": 6, "model": "Claude Haiku 4.5", "omp_argument": "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0", "output_price_usd_per_1m": 5.00 }
    ],
    "slow": [
      { "rank": 1, "model": "Kimi K2 Thinking", "omp_argument": "amazon-bedrock/moonshot.kimi-k2-thinking", "output_price_usd_per_1m": 2.50 },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "output_price_usd_per_1m": 3.20 },
      { "rank": 3, "model": "Claude Opus 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-opus-5", "output_price_usd_per_1m": 25.00 }
    ]
  }
}
```

### Value (best value → worst per role)

```json
{
  "performance_price": {
    "default": [
      { "rank": 1, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0", "value_score": 1.11 },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "value_score": 0.94 },
      { "rank": 3, "model": "DeepSeek V3.2", "omp_argument": "amazon-bedrock/deepseek.v3.2", "value_score": 0.46 },
      { "rank": 4, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5", "value_score": 0.40 }
    ],
    "smol": [
      { "rank": 1, "model": "Nova Lite", "omp_argument": "amazon-bedrock/us.amazon.nova-lite-v1:0", "value_score": 8.33 },
      { "rank": 2, "model": "GLM 4.7 Flash", "omp_argument": "amazon-bedrock/zai.glm-4.7-flash", "value_score": 7.50 },
      { "rank": 3, "model": "Nova Micro", "omp_argument": "amazon-bedrock/us.amazon.nova-micro-v1:0", "value_score": 7.14 },
      { "rank": 4, "model": "MiniMax M2.5", "omp_argument": "amazon-bedrock/minimax.minimax-m2.5", "value_score": 3.33 },
      { "rank": 5, "model": "Kimi K2.5", "omp_argument": "amazon-bedrock/moonshotai.kimi-k2.5", "value_score": 1.67 },
      { "rank": 6, "model": "Claude Haiku 4.5", "omp_argument": "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0", "value_score": 1.20 }
    ],
    "slow": [
      { "rank": 1, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "value_score": 0.63 },
      { "rank": 2, "model": "Kimi K2 Thinking", "omp_argument": "amazon-bedrock/moonshot.kimi-k2-thinking", "value_score": 0.40 },
      { "rank": 3, "model": "Claude Opus 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-opus-5", "value_score": 0.12 }
    ]
  }
}
```

### Ready-to-use omp config commands

```bash
# Performance-focused (best model per role)
omp config set modelRoles '{
  "default": "amazon-bedrock/us.anthropic.claude-sonnet-5",
  "smol":    "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0",
  "slow":    "amazon-bedrock/us.anthropic.claude-opus-5"
}'

# Price-focused (cheapest model per role that still exists)
omp config set modelRoles '{
  "default": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0",
  "smol":    "amazon-bedrock/us.amazon.nova-micro-v1:0",
  "slow":    "amazon-bedrock/moonshot.kimi-k2-thinking"
}'

# Value-focused (best pts/$ per role)
omp config set modelRoles '{
  "default": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0",
  "smol":    "amazon-bedrock/us.amazon.nova-lite-v1:0",
  "slow":    "amazon-bedrock/zai.glm-5"
}'

# Current adopted config (Chinese-origin models)
omp config set modelRoles '{
  "default": "amazon-bedrock/zai.glm-5",
  "smol":    "amazon-bedrock/minimax.minimax-m2.5",
  "slow":    "amazon-bedrock/moonshotai.kimi-k2.5"
}'
```

---

## 5. Open questions / follow-ups

- Re-run performance ranking once independent evals (SWE-bench, LMArena, Artificial Analysis) cover Claude Sonnet 5 / Opus 5 / GLM 5.
- Verify Nova Premier/Nova Pro availability if they reappear in the catalog.
- Confirm `moonshot.kimi-k2-thinking` vs `moonshotai.kimi-k2-5` vendor prefix consistency — both exist and work.
- Add DeepSeek R1 if/when it appears on Bedrock.
