# Cost Optimization Feature - Product Requirements Document

## Overview
Implement configurable cost/quality modes for the Arakis systematic review pipeline to reduce API costs while maintaining acceptable quality.

## Goals
- Reduce per-review costs by 50-95% depending on mode
- Maintain configurability for different use cases
- Store mode selection per workflow for audit trail
- Provide backend configuration with optional settings UI for testing

## Non-Goals
- Real-time cost estimation UI
- A/B testing framework
- Per-stage model selection (simplified presets only)

---

## Mode Definitions

### Mode: QUALITY
**Target:** Maximum accuracy, highest cost
**Use Case:** Publication-quality systematic reviews, final analyses

| Stage | Model | Passes | Full Text |
|-------|-------|--------|-----------|
| Screening | gpt-5-mini | Dual (2x) | **Yes (Full)** |
| Extraction | gpt-5-mini | Triple (3x) | **Yes (Full)** |
| Writing | gpt-5.2-2025-12-11 | Single (max reasoning) | N/A |
| **Est. Cost (50 papers, 20 included)** | | | **~$TBD** |

**Note:** QUALITY mode always uses full text for screening and extraction - never abstract-only.

### Mode: BALANCED (Default/Recommended)
**Target:** Good quality at reasonable cost
**Use Case:** Most systematic reviews, iterative research

| Stage | Model | Passes | Full Text |
|-------|-------|--------|-----------|
| Screening | gpt-5-nano | Single (1x) | **Yes (Full)** |
| Extraction | gpt-5-nano | Single (1x) | **Yes (Full)** |
| PRISMA | **Programmatic SVG** | N/A | N/A |
| Writing | o3-mini | Single | N/A |
| **Est. Cost (50 papers, 20 included)** | | | **~$TBD** |

**Note:** PRISMA is ALWAYS generated programmatically (SVG), never by LLM, in all modes.

### Mode: FAST
**Target:** Speed over everything - skip non-essential stages
**Use Case:** Preliminary screening, scoping reviews, testing hypotheses

| Stage | Model | Passes | Full Text | Notes |
|-------|-------|--------|-----------|-------|
| Screening | gpt-5-nano | Single (1x) | **Yes (Full)** | |
| Extraction | gpt-5-nano | Single (1x) | **Yes (Full)** | |
| RoB | **SKIPPED** | - | - | Skip risk of bias assessment |
| Analysis | **SKIPPED** | - | - | Skip meta-analysis |
| PRISMA | **Programmatic SVG** | N/A | N/A | |
| Writing | o3-mini | Single | N/A | Minimal sections |
| **Est. Cost (50 papers, 20 included)** | | | **~$TBD** |

**Note:** FAST mode skips RoB and Analysis stages. PRISMA is ALWAYS programmatic in all modes.

### Mode: ECONOMY
**Target:** Absolute minimum cost - bare essentials only
**Use Case:** Proof of concept, educational use, very large reviews

| Stage | Model | Passes | Full Text | Notes |
|-------|-------|--------|-----------|-------|
| Screening | gpt-5-nano | Single (1x) | **Yes (Full)** | |
| Extraction | gpt-5-nano | Single (1x) | **Yes (Full)** | |
| RoB | **SKIPPED** | - | - | Skip risk of bias |
| Analysis | **SKIPPED** | - | - | Skip meta-analysis |
| PRISMA | **Programmatic SVG** | N/A | N/A | |
| Writing | o3-mini | Single (minimal) | N/A | Abstract + summary only |
| **Est. Cost (50 papers, 20 included)** | | | **~$TBD** |

**Note:** ECONOMY mode skips RoB and Analysis. **PRISMA is ALWAYS programmatic in ALL modes.**

---

## PRISMA Diagram - ALWAYS PROGRAMMATIC

**CRITICAL RULE: PRISMA is ALWAYS generated programmatically as SVG. Never use LLM for PRISMA in any mode.**

### Why Programmatic?
1. **Zero API cost** - No LLM calls
2. **100% accuracy** - Mathematical precision vs LLM hallucinations
3. **Instant generation** - No latency
4. **Standard compliant** - Follows PRISMA 2020 specification exactly

### Implementation
- Reference: https://estech.shinyapps.io/prisma_flowdiagram/
- Output: SVG format (scalable, embeddable)
- Input: Paper counts from workflow stages
- All modes use the same programmatic generator

---

## Technical Requirements

### Backend Changes

#### 1. Database Schema
Add to `workflows` table:
```sql
ALTER TABLE workflows ADD COLUMN cost_mode VARCHAR(20) DEFAULT 'QUALITY';
```

#### 2. Configuration System
Create `src/arakis/config/cost_modes.py`:
- Mode enum (QUALITY, BALANCED, FAST, ECONOMY)
- Per-mode configuration dataclass
- Mapping to model selections

#### 3. Model Configuration
Update `src/arakis/agents/models.py`:
- Dynamic model selection based on mode
- Fallback chain if model unavailable

#### 4. Agent Updates
Update all agents to read mode from config:
- `screener.py` - dual_review flag
- `extractor.py` - triple_review flag, use_full_text flag
- Writing agents - model selection

#### 5. Workflow Orchestrator
- Accept mode parameter on workflow creation
- Store in workflow record
- Pass to all stage executors

#### 6. Cost Tracking
- Track actual API usage per workflow
- Calculate and store final cost at workflow completion
- Store in workflow metrics (not real-time tracking)

### Frontend Changes (Settings Only)

#### Settings Page Addition
Add to admin/developer settings:
```
Default Cost Mode: [QUALITY ▼]
- QUALITY: Maximum accuracy (~$15/50 papers)
- BALANCED: Good quality, reasonable cost (~$4/50 papers)
- FAST: Quick results (~$1.50/50 papers)
- ECONOMY: Minimum cost (~$0.80/50 papers)
```

Note: This is for development/testing only. Production will use backend config.

---

## API Changes

### Workflow Creation
```json
POST /api/workflows
{
  "research_question": "...",
  "cost_mode": "BALANCED",  // Optional, defaults to config
  ...
}
```

### Workflow Response
```json
{
  "id": "...",
  "cost_mode": "BALANCED",
  "estimated_cost": 4.0,
  "actual_cost": null,  // populated on completion
  ...
}
```

---

## Testing Requirements

### Unit Tests (All Modes)
1. Mode configuration loads correctly
2. Each mode maps to correct models
3. Agents receive correct flags (dual_review, triple_review, etc.)
4. Workflow stores mode in database
5. Cost tracking accumulates correctly

### Integration Tests (Mocked)
1. Full pipeline runs with each mode
2. Mode changes affect API call counts
3. Cost estimates are reasonable

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Create cost mode configuration system
- [ ] Add database migration for cost_mode column
- [ ] Update model configuration to be dynamic
- [ ] Unit tests

### Phase 2: Agent Integration
- [ ] Update screener to use mode config
- [ ] Update extractor to use mode config
- [ ] Update writing agents to use mode config
- [ ] Unit tests

### Phase 3: Orchestrator Integration
- [ ] Workflow creation accepts mode parameter
- [ ] Orchestrator passes mode to stages
- [ ] Cost tracking implementation
- [ ] Unit tests

### Phase 4: Settings UI (Optional)
- [ ] Add mode selector to settings page
- [ ] Display mode in workflow details

### Phase 5: PRISMA Programmatic (REQUIRED - All Modes)
- [ ] Implement SVG PRISMA generator
- [ ] Remove ALL LLM PRISMA generation code
- [ ] Unit tests with various paper counts

**CRITICAL:** PRISMA is ALWAYS programmatic. No LLM PRISMA exists in any mode.

---

## Cost Model Reference

| Model | Input $/1M | Output $/1M | Notes |
|-------|-----------|-------------|-------|
| o1 | $15.00 | $60.00 | Extended thinking |
| o3-mini | $1.10 | $4.40 | Faster reasoning |
| gpt-4o | $2.50 | $10.00 | Default quality |
| gpt-5-nano | TBD | TBD | New nano model |

---

## Success Metrics

1. **Cost Reduction:** BALANCED mode costs <30% of QUALITY mode
2. **Quality Maintenance:** Spot-check 10 papers show >90% agreement
3. **Performance:** No significant latency increase in FAST mode
4. **Adoption:** Mode stored correctly for 100% of workflows

---

## Open Questions

1. Should we validate that BALANCED mode produces acceptable results before making it default?
2. Do we need a "custom" mode for power users to tweak individual settings?
3. Should we add cost alerts (e.g., warn if review will cost >$50)?

---

## Appendix: Current vs Target Costs

| Scenario | QUALITY | BALANCED (Default) | FAST | ECONOMY |
|----------|---------|-------------------|------|---------|
| Small review (20 papers) | ~$TBD | ~$TBD | ~$TBD | ~$TBD |
| Medium review (50 papers) | ~$TBD | ~$TBD | ~$TBD | ~$TBD |
| Large review (200 papers) | ~$TBD | ~$TBD | ~$TBD | ~$TBD |

**Default Mode:** BALANCED (good quality at reasonable cost)

**Stage Skipping Summary:**
- QUALITY: All 12 stages
- BALANCED: All 12 stages (cheaper models)
- FAST: Skips RoB + Analysis stages
- ECONOMY: Skips RoB + Analysis, uses programmatic PRISMA
