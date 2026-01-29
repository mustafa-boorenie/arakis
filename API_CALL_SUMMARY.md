# Arakis Screening Workflow - API Call Summary

This document shows every API call made during the screening workflow, step by step.

## Overview

| Stage | API Calls | Cost |
|-------|-----------|------|
| Search (Query Gen) | 1 | ~$0.04 |
| Search (PubMed) | 2 | $0.00 |
| Search (OpenAlex) | 1 | $0.00 |
| Screening (per paper) | 2 (dual-review) | ~$0.04 |
| **Total (100 papers)** | **~204** | **~$4.24** |

---

## STAGE 1: SEARCH

### Step 1.1: Query Generation (OpenAI)

**API Call:**
```http
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer sk-...
Content-Type: application/json

{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert medical librarian and systematic review specialist..."
    },
    {
      "role": "user",
      "content": "Research Question: Effect of aspirin on mortality in sepsis patients\n\nGenerate 3 search query variations..."
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "extract_pico",
        "parameters": {
          "type": "object",
          "properties": {
            "population": {"type": "string"},
            "intervention": {"type": "string"},
            "comparison": {"type": "string"},
            "outcome": {"type": "string"}
          }
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "generate_pubmed_query",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "explanation": {"type": "string"}
          }
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

**Response:**
```json
{
  "id": "chatcmpl-1234567890",
  "model": "gpt-4o",
  "choices": [{
    "message": {
      "tool_calls": [
        {
          "function": {
            "name": "extract_pico",
            "arguments": {
              "population": "Sepsis patients",
              "intervention": "Aspirin therapy",
              "comparison": "Placebo or standard care",
              "outcome": "Mortality"
            }
          }
        },
        {
          "function": {
            "name": "generate_pubmed_query",
            "arguments": {
              "query": "(((\"Sepsis\"[Mesh]) OR \"Severe Sepsis\"[Mesh]) OR \"Septic Shock\"[Mesh]) AND ((\"Aspirin\"[Mesh]) OR \"Acetylsalicylic Acid\"[Mesh]) AND ((\"Mortality\"[Mesh]) OR \"Death\"[Mesh] OR \"Survival\"[Mesh])",
              "explanation": "Broad search using MeSH terms"
            }
          }
        }
      ]
    }
  }],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 380,
    "total_tokens": 1630
  }
}
```

**Timing:** ~2.8 seconds  
**Cost:** ~$0.04

---

### Step 1.2: PubMed Search (NCBI E-utilities)

**API Call:**
```http
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
?db=pubmed
&term=((("Sepsis"[Mesh]) OR "Severe Sepsis"[Mesh]) OR "Septic Shock"[Mesh]) AND (("Aspirin"[Mesh]) OR "Acetylsalicylic Acid"[Mesh]) AND (("Mortality"[Mesh]) OR "Death"[Mesh] OR "Survival"[Mesh])
&retmax=100
&retmode=json
```

**Response:**
```json
{
  "esearchresult": {
    "count": "247",
    "retmax": "100",
    "retstart": "0",
    "idlist": [
      "38012345",
      "37987654",
      "37890123",
      "37789012",
      "37678901"
    ],
    "querytranslation": "(\"Sepsis\"[MeSH Terms])..."
  }
}
```

**Timing:** ~450ms  
**Cost:** Free (with API key: 10 req/sec)

---

### Step 1.3: PubMed Details (E-summary)

**API Call:**
```http
GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi
?db=pubmed
&id=38012345,37987654,37890123
&retmode=json
```

**Response:**
```json
{
  "result": {
    "38012345": {
      "uid": "38012345",
      "title": "Aspirin use and mortality in sepsis: a systematic review and meta-analysis",
      "authors": [
        {"name": "Smith J", "authtype": "Author"},
        {"name": "Jones M", "authtype": "Author"}
      ],
      "fulljournalname": "Critical Care Medicine",
      "pubdate": "2023 Oct",
      "doi": "10.1097/CCM.0000000000001234"
    }
  }
}
```

**Timing:** ~320ms  
**Cost:** Free

---

### Step 1.4: OpenAlex Search

**API Call:**
```http
GET https://api.openalex.org/works
?search=sepsis aspirin mortality
&filter=publication_year:>2015
&per_page=100
&mailto=researcher@example.com
```

**Response:**
```json
{
  "meta": {
    "count": 156,
    "db_response_time_ms": 45
  },
  "results": [
    {
      "id": "W1234567890",
      "title": "Effect of aspirin on sepsis outcomes",
      "publication_year": 2022,
      "authors": [{"author": {"display_name": "Johnson A"}}],
      "host_venue": {"display_name": "Journal of Critical Care"},
      "doi": "https://doi.org/10.1016/j.jcrc.2022.05.001"
    }
  ]
}
```

**Timing:** ~180ms  
**Cost:** Free (polite pool with email)

---

### Step 1.5: Deduplication (Internal Processing)

No external API calls - pure Python processing using:
- DOI matching (exact)
- PMID matching (exact)
- Title fuzzy matching (rapidfuzz, >90% similarity)

**Results:**
```
Before:  147 papers (PubMed: 100, OpenAlex: 47)
After:   103 papers
Removed: 44 duplicates
```

---

## STAGE 2: SCREENING

For each paper, the screening stage makes **2 API calls** (dual-review mode) or **1 API call** (fast mode).

### Per-Paper Screening (Dual-Review Mode)

#### Pass 1: Temperature 0.3 (Consistent)

**API Call:**
```http
POST https://api.openai.com/v1/chat/completions
Authorization: Bearer sk-...
Content-Type: application/json

{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are an expert systematic reviewer screening papers for inclusion.\n\nInclusion criteria:\n- Human RCTs\n- Sepsis patients\n- Mortality outcome\n\nExclusion criteria:\n- Animal studies\n- Reviews\n- Case reports\n\nSCREENING RULES:\n1. INCLUDE: Paper clearly meets all inclusion criteria...\n2. EXCLUDE: Paper clearly meets any exclusion criteria...\n3. MAYBE: Paper is unclear - insufficient information..."
    },
    {
      "role": "user",
      "content": "Title: Aspirin use and mortality in sepsis: a systematic review and meta-analysis\n\nAbstract: Background: Aspirin may improve outcomes in sepsis... Methods: We conducted a systematic review... Results: 15 RCTs included...\n\nYear: 2023\nJournal: Critical Care Medicine\nPublication Types: Meta-Analysis, Systematic Review\n\nScreen this paper."
    }
  ],
  "tools": [{
    "type": "function",
    "function": {
      "name": "screen_paper",
      "parameters": {
        "type": "object",
        "properties": {
          "decision": {
            "enum": ["INCLUDE", "EXCLUDE", "MAYBE"],
            "description": "The screening decision"
          },
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          },
          "reason": {"type": "string"},
          "matched_inclusion": {
            "type": "array",
            "items": {"type": "string"}
          },
          "matched_exclusion": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "required": ["decision", "confidence", "reason"]
      }
    }
  }],
  "tool_choice": {
    "type": "function",
    "function": {"name": "screen_paper"}
  },
  "temperature": 0.3
}
```

**Response:**
```json
{
  "id": "chatcmpl-screen1",
  "choices": [{
    "message": {
      "tool_calls": [{
        "function": {
          "name": "screen_paper",
          "arguments": {
            "decision": "EXCLUDE",
            "confidence": 0.95,
            "reason": "This is a systematic review and meta-analysis, not a primary RCT. It synthesizes existing studies rather than reporting original research.",
            "matched_inclusion": [],
            "matched_exclusion": ["Reviews"]
          }
        }
      }]
    }
  }],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 85
  }
}
```

**Timing:** ~1.25 seconds  
**Cost:** ~$0.02

---

#### Pass 2: Temperature 0.7 (Creative)

**API Call:**
```http
POST https://api.openai.com/v1/chat/completions

{
  "model": "gpt-4o",
  "messages": [ /* Same as Pass 1 */ ],
  "tools": [ /* Same tool definition */ ],
  "tool_choice": {
    "type": "function",
    "function": {"name": "screen_paper"}
  },
  "temperature": 0.7  // <-- Only difference: higher temperature
}
```

**Response:**
```json
{
  "id": "chatcmpl-screen2",
  "choices": [{
    "message": {
      "tool_calls": [{
        "function": {
          "name": "screen_paper",
          "arguments": {
            "decision": "EXCLUDE",
            "confidence": 0.92,
            "reason": "Publication type is Systematic Review/Meta-Analysis, not a primary study.",
            "matched_inclusion": [],
            "matched_exclusion": ["Reviews"]
          }
        }
      }]
    }
  }],
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 80
  }
}
```

**Timing:** ~1.32 seconds  
**Cost:** ~$0.02

---

### Conflict Detection

When Pass 1 and Pass 2 disagree:

```python
if decision1.status != decision2.status:
    decision.is_conflict = True
    decision.status = "MAYBE"  # Default to MAYBE on conflict
    decision.confidence = min(d1.confidence, d2.confidence) * 0.5
```

**Example Conflict:**
```
Pass 1: INCLUDE (0.92 confidence)
Pass 2: MAYBE (0.65 confidence)

Resolution:
- Status: MAYBE
- Confidence: 0.33 (min * 0.5)
- Flagged for human review
```

---

## Batch Processing

Papers are processed in concurrent batches (default: 5 papers at a time).

### For 100 Papers:

```
Batch Size: 5 papers
Total Batches: 20
Concurrent API Calls per Batch: 10 (5 papers × 2 passes)
Sequential Batches: 20

Time Estimate:
- Per batch: ~2.5 seconds
- Total: ~50 seconds (20 batches × 2.5s)
- With rate limiting: ~2-3 minutes
```

---

## Cost Breakdown (100 Papers)

| Component | API Calls | Tokens | Cost |
|-----------|-----------|--------|------|
| Query Generation | 1 | 1,630 | $0.04 |
| Screening Pass 1 | 100 | ~53,500 | $1.34 |
| Screening Pass 2 | 100 | ~53,000 | $1.33 |
| PubMed Searches | 2 | N/A | Free |
| OpenAlex | 1 | N/A | Free |
| **TOTAL** | **204** | **~108K** | **~$2.71** |

*Note: Cost estimates based on GPT-4o pricing ($0.0025/1K input, $0.01/1K output)*

---

## Rate Limiting

The system respects rate limits:

```python
# OpenAI Rate Limiter
- Free tier: 3 requests/minute
- Paid tier: 500+ requests/minute

# PubMed Rate Limiter  
- Without API key: 3 requests/second
- With API key: 10 requests/second

# OpenAlex Rate Limiter
- Default: 100 requests/5 minutes
- Polite pool (with email): Better limits
```

**Retry Logic:**
```python
@retry_with_exponential_backoff(max_retries=8, initial_delay=2.0)
async def _call_openai(messages, tools):
    # Exponential backoff: 2s → 4s → 8s → 16s...
    # Max delay: 90 seconds
```

---

## Response Format (Final Output)

```json
{
  "total_screened": 100,
  "included": 42,
  "excluded": 52,
  "maybe": 6,
  "conflicts": 8,
  "decisions": [
    {
      "paper_id": "pubmed_38012345",
      "status": "INCLUDE",
      "reason": "RCT with sepsis patients measuring mortality",
      "confidence": 0.92,
      "matched_inclusion": ["Human RCTs", "Sepsis patients"],
      "matched_exclusion": [],
      "is_conflict": false
    },
    {
      "paper_id": "pubmed_37987654",
      "status": "MAYBE",
      "reason": "CONFLICT: First pass: INCLUDE, Second pass: MAYBE. Original reason: Unclear population",
      "confidence": 0.33,
      "matched_inclusion": [],
      "matched_exclusion": [],
      "is_conflict": true
    }
  ],
  "included_paper_ids": [
    "pubmed_38012345",
    "pubmed_37890123",
    ...
  ]
}
```

---

## Monitoring & Debugging

### Progress Logging
```
[screen] Screening ALL 100 papers (dual_review=True)
[screen] Progress: 10/100 papers screened (10%)
[screen] Progress: 20/100 papers screened (20%)
...
[screen] Progress: 100/100 papers screened (100%)
[screen] Completed screening: 42 included, 52 excluded, 6 maybe
```

### Error Handling
```python
# If rate limit hit:
[yellow]Rate limit hit. Retrying in 4.2s (attempt 1/8)...[/yellow]

# If all retries fail:
[red]Rate limit exceeded after 8 retries. Please wait a few minutes.[/red]

# Stage result:
{
  "success": false,
  "error": "Rate limit exceeded",
  "needs_user_action": true,
  "action_required": "Please wait a few minutes and retry"
}
```

---

## Key Takeaways

1. **Dual-review mode** = 2 API calls per paper (higher accuracy, ~40% higher cost)
2. **Fast mode** = 1 API call per paper (faster, cheaper)
3. **Batch processing** = 5 papers concurrently (configurable)
4. **Conflict detection** = Automatic flagging of disagreements
5. **Cost scales linearly** = 100 papers ≈ $2.70 for screening
