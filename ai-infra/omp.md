# OMP Model Roles — Bedrock Research Notes

Research for `omp config set modelRoles`, evaluating Chinese-origin models (DeepSeek, Moonshot AI/Kimi, Qwen, Z.AI/GLM, MiniMax) and Amazon Nova against the currently configured Anthropic models, for the three omp roles: `default`, `smol`, `slow`.

Current config:

```json
{
  "default": "amazon-bedrock/us.anthropic.claude-sonnet-5",
  "smol":    "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0",
  "slow":    "amazon-bedrock/us.anthropic.claude-opus-5"
}
```

**Sources:** `docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html` (catalog + model IDs + capability tables) and `aws.amazon.com/bedrock/pricing/` (all $ figures), fetched live. Date of research: 2026-09-21.

**Important caveat:** Performance rankings below are `[INFERENCE]`, not benchmark results. AWS's model-card pages publish zero benchmark scores, and Claude Sonnet 5 / Opus 5 / Kimi K3 / GLM 5 are all too recent for third-party evals to exist. Rankings are derived from: (1) each model card's own positioning language, (2) spec parity (context window, max output tokens) vs. the Claude model in that role, (3) directional reputation of that model family's prior generation on public benchmarks. Price figures are hard data pulled directly from the AWS pricing page and are not inference.

---

## 1. Bedrock catalog — Chinese-origin providers

| Provider | Models available on Bedrock (as of research date) |
|---|---|
| DeepSeek | DeepSeek V3.2, DeepSeek-V3.1, DeepSeek-R1 |
| Moonshot AI (Kimi) | Kimi K3, Kimi K2.5, Kimi K2 Thinking |
| Qwen (Alibaba) | Qwen3 235B A22B 2507, Qwen3 32B, Qwen3 Coder 480B A35B Instruct, Qwen3 Coder Next, Qwen3 Next 80B A3B, Qwen3 VL 235B A22B, Qwen3-Coder-30B-A3B-Instruct |
| Z.AI (GLM) | GLM 4.7, GLM 4.7 Flash, GLM 5 |
| MiniMax | MiniMax M2, MiniMax M2.1, MiniMax M2.5 |

Amazon's own models considered as alternatives: Nova Micro, Nova Lite, Nova Pro, Nova Premier.

⚠️ **Nova Premier flag:** its model card lists `Model lifecycle: Legacy`, `Model EOL date: September 14, 2026` — already past as of this research date. Confirm it's still invokable in-account before relying on it.

---

## 2. Master pricing table

US East (N. Virginia/Ohio/Oregon), Standard on-demand tier, USD per 1M tokens. "Not supported" = the model's Bedrock capability table has no caching/batch section at all (grounded per model card). "Not published" = feature is listed as supported but AWS's pricing page shows no rate for it.

| Model | omp argument | Input | Output | Cache Write (5m/1h) | Cache Read | Batch (in/out) | Priority (+75%) | Flex (−50%) |
|---|---|---|---|---|---|---|---|---|
| Claude Opus 5 | `amazon-bedrock/us.anthropic.claude-opus-5` | $5.00 | $25.00 | $6.25 / $10.00 | $0.50 | $2.50 / $12.50 | ✗ | ✗ |
| Claude Sonnet 5 | `amazon-bedrock/us.anthropic.claude-sonnet-5` | $2.00 | $10.00 | $2.50 / $4.00 | $0.20 | Not supported | ✗ | ✗ |
| Claude Haiku 4.5 | `amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0` | $1.00 | $5.00 | $1.25 / $2.00 | $0.10 | $0.50 / $2.50 | ✗ | ✗ |
| Nova Premier ⚠️ | `amazon-bedrock/us.amazon.nova-premier-v1:0` | $2.50 | $12.50 | Not published | Not published | Not published | ✓ | ✓ |
| Nova Pro | `amazon-bedrock/us.amazon.nova-pro-v1:0` | $0.80 | $3.20 | Not published | Not published | Not published | not verified | not verified |
| Nova Lite | `amazon-bedrock/us.amazon.nova-lite-v1:0` | $0.06 | $0.24 | Not published | Not published | Not published | not verified | not verified |
| Nova Micro | `amazon-bedrock/us.amazon.nova-micro-v1:0` | $0.035 | $0.14 | Not published | Not published | Not published | not verified | not verified |
| Kimi K3 (global CRIS) | `amazon-bedrock/global.moonshotai.kimi-k3` | $3.00 | $15.00 | $3.75 (30m only) | $0.30 | Not supported | ✓ | ✓ |
| GLM 5 | `amazon-bedrock/zai.glm-5` | $1.00 | $3.20 | Not supported | Not supported | $0.50 / $1.60 | ✓ | ✓ |
| Qwen3 Coder 480B A35B | `amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0` | $0.45 | $1.80 | Not supported | Not supported | $0.225 / $0.90 | ✓ | ✓ |
| Kimi K2 Thinking | `amazon-bedrock/moonshot.kimi-k2-thinking` | $0.60 | $2.50 | Not supported | Not supported | Not supported | ✓ | ✓ |
| Kimi K2.5 | `amazon-bedrock/moonshotai.kimi-k2.5` | $0.60 | $3.00 | Not supported | Not supported | Not supported | ✓ | ✓ |
| MiniMax M2.5 | `amazon-bedrock/minimax.minimax-m2.5` | $0.30 | $1.20 | Not supported | Not supported | Not supported | ✓ | ✓ |
| GLM 4.7 Flash | `amazon-bedrock/zai.glm-4.7-flash` | $0.07 | $0.40 | Not supported | Not supported | $0.035 / $0.20 | ✓ | ✓ |

**Notable:** Only Claude, Nova, and Kimi K3 support prompt caching at all on Bedrock. Every other model here (GLM, Qwen, MiniMax, Kimi K2.x) pays full input price on every turn — no discount for repeated system prompts/tool schemas. This can flip the "cheaper on paper" story for chatty agent loops.

⚠️ Kimi K3's Bedrock Runtime `us.` vs `global.` profile changes price 10%: US CRIS = $3.30/$16.50, Global CRIS = $3.00/$15.00 (used above).
⚠️ Kimi K2 Thinking's model ID has an inconsistent vendor prefix across AWS's own docs: Bedrock Runtime Invoke sample uses `moonshot.kimi-k2-thinking`; the Mantle-endpoint sample uses `moonshotai.kimi-k2-thinking`. Try the former first.

---

## 3. Rankings per role

Performance rank = `[INFERENCE]` (see caveat above). Price rank = ascending output-token price (output dominates cost in agentic/coding loops). Value rank = performance points (best=N, worst=1) ÷ output price — rewards models that outperform their price tier.

### `default` (competing with Claude Sonnet 5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Sonnet 5 | 1 | 4 ($10.00) | 5/10.00 = 0.50 | 3 |
| Kimi K3 | 2 | 5 ($15.00) | 4/15.00 = 0.27 | 5 |
| GLM 5 | 3 | 2 ($3.20) | 3/3.20 = 0.94 | 2 |
| Qwen3 Coder 480B | 4 | 1 ($1.80) | 2/1.80 = 1.11 | 1 |
| Nova Pro | 5 | 3 ($3.20) | 1/3.20 = 0.31 | 4 |

### `smol` (competing with Claude Haiku 4.5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Haiku 4.5 | 1 | 6 ($5.00) | 6/5.00 = 1.20 | 6 |
| Kimi K2.5 | 2 | 5 ($3.00) | 5/3.00 = 1.67 | 5 |
| MiniMax M2.5 | 3 | 4 ($1.20) | 4/1.20 = 3.33 | 4 |
| GLM 4.7 Flash | 4 | 3 ($0.40) | 3/0.40 = 7.50 | 2 |
| Nova Lite | 5 | 2 ($0.24) | 2/0.24 = 8.33 | 1 |
| Nova Micro | 6 | 1 ($0.14) | 1/0.14 = 7.14 | 3 |

⚠️ In `smol`, performance and price rank move in almost perfect lockstep (a near-ordered price/performance ladder), so this role's value spread is the most sensitive to the inferred performance ordering — trust it least of the three roles.

### `slow` (competing with Claude Opus 5)

| Model | Performance Rank | Price Rank | Value Score (pts/$) | Value Rank |
|---|---|---|---|---|
| Claude Opus 5 | 1 | 5 ($25.00) | 5/25.00 = 0.20 | 5 |
| Kimi K3 | 2 | 4 ($15.00) | 4/15.00 = 0.27 | 3 |
| Nova Premier ⚠️ | 3 | 3 ($12.50) | 3/12.50 = 0.24 | 4 |
| GLM 5 | 4 | 2 ($3.20) | 2/3.20 = 0.63 | 1 |
| Kimi K2 Thinking | 5 | 1 ($2.50) | 1/2.50 = 0.40 | 2 |

**Reading these:** the current Claude model lands near the bottom of the value rank in every role — it's #1 on raw performance but priciest, so performance-per-dollar is diluted. Value rank tells you where to switch if cost is the binding constraint; performance rank tells you where to switch if quality is.

---

## 4. JSON exports

### Performance rank (per role, best → worst)

```json
{
  "performance": {
    "default": [
      { "rank": 1, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5" },
      { "rank": 2, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3" },
      { "rank": 3, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5" },
      { "rank": 4, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0" },
      { "rank": 5, "model": "Nova Pro", "omp_argument": "amazon-bedrock/us.amazon.nova-pro-v1:0" }
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
      { "rank": 2, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3" },
      { "rank": 3, "model": "Nova Premier", "omp_argument": "amazon-bedrock/us.amazon.nova-premier-v1:0", "flag": "legacy/EOL, verify availability" },
      { "rank": 4, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5" },
      { "rank": 5, "model": "Kimi K2 Thinking", "omp_argument": "amazon-bedrock/moonshot.kimi-k2-thinking" }
    ]
  }
}
```

### Price rank (per role, cheapest → priciest, by output $/1M tokens)

```json
{
  "price": {
    "default": [
      { "rank": 1, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0", "output_price_usd_per_1m": 1.80 },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "output_price_usd_per_1m": 3.20 },
      { "rank": 3, "model": "Nova Pro", "omp_argument": "amazon-bedrock/us.amazon.nova-pro-v1:0", "output_price_usd_per_1m": 3.20 },
      { "rank": 4, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5", "output_price_usd_per_1m": 10.00 },
      { "rank": 5, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3", "output_price_usd_per_1m": 15.00 }
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
      { "rank": 3, "model": "Nova Premier", "omp_argument": "amazon-bedrock/us.amazon.nova-premier-v1:0", "output_price_usd_per_1m": 12.50, "flag": "legacy/EOL, verify availability" },
      { "rank": 4, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3", "output_price_usd_per_1m": 15.00 },
      { "rank": 5, "model": "Claude Opus 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-opus-5", "output_price_usd_per_1m": 25.00 }
    ]
  }
}
```

### Performance/price (value) rank (per role, best value → worst)

Value score = performance points (best=N, worst=1 within that role) ÷ output price ($/1M tokens). Higher score = better value.

```json
{
  "performance_price": {
    "default": [
      { "rank": 1, "model": "Qwen3 Coder 480B A35B", "omp_argument": "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0", "value_score": 1.11 },
      { "rank": 2, "model": "GLM 5", "omp_argument": "amazon-bedrock/zai.glm-5", "value_score": 0.94 },
      { "rank": 3, "model": "Claude Sonnet 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-sonnet-5", "value_score": 0.50 },
      { "rank": 4, "model": "Nova Pro", "omp_argument": "amazon-bedrock/us.amazon.nova-pro-v1:0", "value_score": 0.31 },
      { "rank": 5, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3", "value_score": 0.27 }
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
      { "rank": 3, "model": "Kimi K3", "omp_argument": "amazon-bedrock/global.moonshotai.kimi-k3", "value_score": 0.27 },
      { "rank": 4, "model": "Nova Premier", "omp_argument": "amazon-bedrock/us.amazon.nova-premier-v1:0", "value_score": 0.24, "flag": "legacy/EOL, verify availability" },
      { "rank": 5, "model": "Claude Opus 5", "omp_argument": "amazon-bedrock/us.anthropic.claude-opus-5", "value_score": 0.20 }
    ]
  }
}
```

---

## 5. Open questions / follow-ups if revisiting this research

- No third-party benchmark data exists yet for Claude Sonnet 5 / Opus 5, Kimi K3, or GLM 5 — re-run performance ranking once independent evals (SWE-bench, LMArena, Artificial Analysis) cover these releases.
- Confirm Nova Premier's actual availability given its EOL date has passed.
- Confirm exact Priority/Flex multipliers for Anthropic and Nova Pro/Lite/Micro (not published on the pricing page at research time; only Kimi/GLM/Qwen/MiniMax publish the 1.75x/0.5x rule directly).
- Confirm `moonshot.kimi-k2-thinking` vs `moonshotai.kimi-k2-thinking` model ID — AWS's own docs are inconsistent.
