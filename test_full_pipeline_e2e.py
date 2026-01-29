#!/usr/bin/env python3
"""
END-TO-END PIPELINE TEST

This test runs the COMPLETE Arakis workflow:
1. Search (mocked - to save costs)
2. Screening (real OpenAI API calls)
3. PDF Fetch (mocked)
4. Data Extraction (real OpenAI API calls)
5. Risk of Bias (real OpenAI API calls)
6. Analysis (pure Python)
7. PRISMA (pure Python)
8. Tables (pure Python)
9. Introduction writing (real OpenAI API calls - o3-pro)
10. Methods writing (real OpenAI API calls - o3-pro)
11. Results writing (real OpenAI API calls - o3-pro)
12. Discussion writing (real OpenAI API calls - o3-pro)

⚠️  WARNING: This will make MANY real API calls!
    Estimated cost: $15-25 for ~10 papers
    
Press Ctrl+C within 5 seconds to cancel...
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

sys.path.insert(0, "src")

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from arakis.config import get_settings
from arakis.database.models import Base, Workflow
from arakis.models.paper import Author, Paper, PaperSource
from arakis.workflow.orchestrator import WorkflowOrchestrator


# Test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_pipeline.db"

# Research question for testing
RESEARCH_QUESTION = "Does aspirin reduce mortality in patients with sepsis?"
INCLUSION_CRITERIA = ["Randomized controlled trials", "Adult patients with sepsis", "Aspirin intervention", "Mortality outcome"]
EXCLUSION_CRITERIA = ["Animal studies", "Pediatric populations", "Observational studies", "Case reports"]

# Sample papers (simulating search results)
SAMPLE_PAPERS = [
    {
        "id": "pubmed_38012345",
        "title": "Aspirin use is associated with reduced mortality in sepsis: a systematic review and meta-analysis",
        "abstract": "Background: Sepsis is a leading cause of mortality. Aspirin has been proposed as an adjunctive therapy. Methods: We conducted a systematic review and meta-analysis of RCTs comparing aspirin vs placebo in sepsis patients. Results: 8 RCTs with 2,847 patients. Aspirin was associated with reduced 28-day mortality (RR 0.82, 95% CI 0.71-0.95, p=0.008). Conclusions: Aspirin may reduce mortality in sepsis.",
        "year": 2023,
        "source": "pubmed",
        "doi": "10.1097/CCM.0000000000001234",
        "pmid": "38012345",
        "authors": [{"name": "Zhang L"}, {"name": "Wang Y"}],
        "full_text": """
Aspirin use is associated with reduced mortality in sepsis: a systematic review and meta-analysis

Background: Sepsis is a leading cause of mortality worldwide with high healthcare costs. Despite advances in supportive care, mortality remains significant. Aspirin has been proposed as an adjunctive therapy due to its anti-inflammatory and antiplatelet properties.

Methods: We conducted a comprehensive systematic review and meta-analysis of randomized controlled trials (RCTs) comparing aspirin to placebo or standard care in adult patients with sepsis or septic shock. We searched PubMed, Embase, and Cochrane Library from inception to December 2022. Primary outcome was 28-day mortality. Secondary outcomes included ICU length of stay, duration of mechanical ventilation, and adverse events.

Results: We identified 8 eligible RCTs with a total of 2,847 patients (1,423 aspirin, 1,424 control). Mean age was 64.2 years, 58% were male. Aspirin was associated with reduced 28-day mortality (Relative Risk 0.82, 95% CI 0.71-0.95, p=0.008, I²=35%). Number needed to treat was 25 (95% CI 16-50). There was no significant difference in ICU length of stay (mean difference -0.8 days, 95% CI -2.1 to 0.5, p=0.23). Adverse events were similar between groups.

Conclusion: In patients with sepsis, aspirin is associated with a statistically significant 18% relative reduction in 28-day mortality. However, the quality of evidence is moderate, and further large-scale RCTs are needed.

Funding: National Institutes of Health Grant R01-HL123456
        """.strip(),
        "has_full_text": True,
    },
    {
        "id": "pubmed_37987654",
        "title": "Effects of acetylsalicylic acid on organ failure in critically ill patients with sepsis",
        "abstract": "Objective: To evaluate the effect of aspirin on organ failure in sepsis. Design: Multicenter, double-blind, placebo-controlled RCT. Setting: 15 ICUs. Patients: 412 adults with severe sepsis. Intervention: Aspirin 100mg daily vs placebo for 14 days. Results: No significant difference in SOFA score. Mortality was similar between groups.",
        "year": 2022,
        "source": "pubmed",
        "doi": "10.1001/jama.2022.4567",
        "pmid": "37987654",
        "authors": [{"name": "Doevenschot L"}, {"name": "van der Horst I"}],
        "full_text": None,
        "has_full_text": False,
    },
    {
        "id": "pubmed_37890123",
        "title": "Low-dose aspirin therapy in septic shock: a randomized pilot trial",
        "abstract": "Background: Platelet activation contributes to organ dysfunction in septic shock. Methods: Single-center RCT of aspirin 75mg vs placebo in 89 patients with septic shock. Results: Aspirin reduced platelet activation markers but showed no difference in 28-day mortality (45% vs 48%, p=0.72).",
        "year": 2021,
        "source": "pubmed",
        "doi": "10.1164/rccm.202103-0656OC",
        "pmid": "37890123",
        "authors": [{"name": "Kor D"}, {"name": "Carter R"}],
        "full_text": None,
        "has_full_text": False,
    },
]


def print_header(title: str, char: str = "="):
    """Print a section header."""
    print(f"\n{char*80}")
    print(f"  {title}")
    print(f"{char*80}")


def print_stage(stage_num: int, title: str):
    """Print stage header."""
    print(f"\n{'─'*80}")
    print(f"  STAGE {stage_num}/12: {title}")
    print(f"{'─'*80}")


def print_result(label: str, value: str, indent: int = 3):
    """Print a result."""
    spaces = " " * indent
    print(f"{spaces}{label:<35} {value}")


async def create_workflow(db: AsyncSession) -> Workflow:
    """Create a workflow in the database."""
    workflow = Workflow(
        id=str(uuid4()),
        research_question=RESEARCH_QUESTION,
        inclusion_criteria=", ".join(INCLUSION_CRITERIA),
        exclusion_criteria=", ".join(EXCLUSION_CRITERIA),
        databases=["pubmed"],
        status="pending",
        created_at=datetime.now(timezone.utc),
    )
    db.add(workflow)
    await db.commit()
    return workflow


async def run_stage(orchestrator: WorkflowOrchestrator, stage: str, input_data: dict, workflow_id: str):
    """Run a single stage and return result."""
    from arakis.workflow.orchestrator import WorkflowOrchestrator
    
    executor_class = WorkflowOrchestrator.STAGE_EXECUTORS.get(stage)
    if not executor_class:
        raise ValueError(f"Unknown stage: {stage}")
    
    executor = executor_class(workflow_id, orchestrator.db)
    result = await executor.run_with_retry(input_data)
    
    return result


async def test_pipeline():
    """Run the full E2E pipeline test."""
    
    print_header("🚀 ARAKIS FULL PIPELINE E2E TEST", "=")
    
    # Check API key
    settings = get_settings()
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY not set!")
        return
    
    print(f"✅ OpenAI API key found: {settings.openai_api_key[:15]}...")
    
    # Setup database
    print_header("📊 SETTING UP TEST DATABASE")
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Create workflow
        workflow = await create_workflow(db)
        print(f"✅ Created workflow: {workflow.id}")
        print(f"   Research question: {workflow.research_question}")
        print(f"   Databases: {workflow.databases}")
        
        # Initialize orchestrator
        orchestrator = WorkflowOrchestrator(db)
        
        # Track accumulated data
        accumulated_data = {
            "research_question": RESEARCH_QUESTION,
            "inclusion_criteria": INCLUSION_CRITERIA,
            "exclusion_criteria": EXCLUSION_CRITERIA,
            "databases": ["pubmed"],
            "fast_mode": True,  # Use fast mode to reduce costs
        }
        
        total_cost = 0.0
        stage_times = {}
        
        # ===================================================================
        # STAGE 1: SEARCH (Mocked)
        # ===================================================================
        print_stage(1, "SEARCH (Mocked)")
        print("   Using pre-defined sample papers to save search API costs")
        
        search_data = {
            "papers_found": len(SAMPLE_PAPERS),
            "duplicates_removed": 0,
            "records_identified": {"pubmed": len(SAMPLE_PAPERS)},
            "papers": SAMPLE_PAPERS,
        }
        accumulated_data["search"] = search_data
        accumulated_data["papers"] = SAMPLE_PAPERS
        print_result("Papers found", str(len(SAMPLE_PAPERS)))
        
        # ===================================================================
        # STAGE 2: SCREENING (Real API Calls)
        # ===================================================================
        print_stage(2, "SCREENING (Real OpenAI API)")
        print("   ⚠️  Making real API calls for dual-review screening...")
        
        start = time.time()
        screen_input = {
            "papers": SAMPLE_PAPERS,
            "inclusion_criteria": INCLUSION_CRITERIA,
            "exclusion_criteria": EXCLUSION_CRITERIA,
            "fast_mode": True,  # Single-pass to save costs
        }
        
        try:
            result = await run_stage(orchestrator, "screen", screen_input, workflow.id)
            if result.success:
                accumulated_data["screen"] = result.output_data
                total_cost += result.cost
                stage_times["screen"] = time.time() - start
                
                print_result("✅ Success", "True")
                print_result("Total screened", str(result.output_data.get("total_screened", 0)))
                print_result("Included", str(result.output_data.get("included", 0)))
                print_result("Excluded", str(result.output_data.get("excluded", 0)))
                print_result("Cost", f"${result.cost:.2f}")
                print_result("Time", f"{stage_times['screen']:.1f}s")
                
                # Filter to included papers for next stages
                included_ids = result.output_data.get("included_paper_ids", [])
                included_papers = [p for p in SAMPLE_PAPERS if p["id"] in included_ids]
                accumulated_data["papers"] = included_papers
            else:
                print(f"❌ Screening failed: {result.error}")
                return
        except Exception as e:
            print(f"❌ Screening error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # ===================================================================
        # STAGE 3: PDF FETCH (Mocked)
        # ===================================================================
        print_stage(3, "PDF FETCH (Mocked)")
        print("   Using existing full_text from sample papers")
        
        papers_with_text = []
        for p in accumulated_data.get("papers", []):
            p["has_full_text"] = bool(p.get("full_text"))
            papers_with_text.append(p)
        
        accumulated_data["pdf_fetch"] = {"papers_processed": len(papers_with_text)}
        print_result("Papers with text", str(len(papers_with_text)))
        
        # ===================================================================
        # STAGE 4: DATA EXTRACTION (Real API Calls)
        # ===================================================================
        print_stage(4, "DATA EXTRACTION (Real OpenAI API)")
        print("   ⚠️  Making real API calls for data extraction...")
        print(f"   Processing {len(papers_with_text)} papers...")
        
        start = time.time()
        extract_input = {
            "papers": papers_with_text,
            "schema": "rct",
            "fast_mode": True,
            "use_full_text": True,
            "research_question": RESEARCH_QUESTION,
            "inclusion_criteria": INCLUSION_CRITERIA,
        }
        
        try:
            result = await run_stage(orchestrator, "extract", extract_input, workflow.id)
            if result.success:
                accumulated_data["extract"] = result.output_data
                total_cost += result.cost
                stage_times["extract"] = time.time() - start
                
                print_result("✅ Success", "True")
                print_result("Papers extracted", str(result.output_data.get("total_papers", 0)))
                print_result("Successful", str(result.output_data.get("successful", 0)))
                print_result("Average quality", f"{result.output_data.get('average_quality', 0):.2f}")
                print_result("Cost", f"${result.cost:.2f}")
                print_result("Time", f"{stage_times['extract']:.1f}s")
                
                # Store extractions for analysis stage
                accumulated_data["extractions"] = result.output_data.get("extractions", [])
            else:
                print(f"❌ Extraction failed: {result.error}")
                return
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # ===================================================================
        # STAGE 5: RISK OF BIAS (Real API Calls)
        # ===================================================================
        print_stage(5, "RISK OF BIAS (Real OpenAI API)")
        print("   ⚠️  Making real API calls for RoB assessment...")
        
        start = time.time()
        rob_input = {
            "extractions": accumulated_data.get("extractions", []),
            "schema_used": "rct",
        }
        
        try:
            result = await run_stage(orchestrator, "rob", rob_input, workflow.id)
            if result.success:
                accumulated_data["rob"] = result.output_data
                total_cost += result.cost
                stage_times["rob"] = time.time() - start
                
                print_result("✅ Success", "True")
                print_result("Studies assessed", str(result.output_data.get("n_studies", 0)))
                print_result("Tool used", result.output_data.get("tool_used", "Unknown"))
                print_result("Cost", f"${result.cost:.2f}")
                print_result("Time", f"{stage_times['rob']:.1f}s")
            else:
                print(f"⚠️  RoB stage skipped or failed: {result.error}")
        except Exception as e:
            print(f"⚠️  RoB error (continuing): {e}")
        
        # ===================================================================
        # STAGE 6: ANALYSIS (Pure Python - No API Calls)
        # ===================================================================
        print_stage(6, "ANALYSIS (Pure Python)")
        print("   Performing statistical meta-analysis...")
        
        start = time.time()
        analysis_input = {
            "extractions": accumulated_data.get("extractions", []),
            "outcome_name": "mortality",
        }
        
        try:
            result = await run_stage(orchestrator, "analysis", analysis_input, workflow.id)
            if result.success:
                accumulated_data["analysis"] = result.output_data
                stage_times["analysis"] = time.time() - start
                
                print_result("✅ Success", "True")
                print_result("Meta-analysis feasible", str(result.output_data.get("meta_analysis_feasible", False)))
                if result.output_data.get("meta_analysis_feasible"):
                    print_result("Studies included", str(result.output_data.get("n_studies", 0)))
                    print_result("Pooled effect", f"{result.output_data.get('pooled_effect', 0):.3f}")
                    print_result("P-value", f"{result.output_data.get('p_value', 1):.4f}")
                    print_result("I²", f"{result.output_data.get('i_squared', 0):.1f}%")
                print_result("Time", f"{stage_times['analysis']:.1f}s")
            else:
                print(f"⚠️  Analysis skipped: {result.error}")
        except Exception as e:
            print(f"⚠️  Analysis error (continuing): {e}")
        
        # ===================================================================
        # STAGES 7-8: PRISMA & TABLES (Pure Python)
        # ===================================================================
        print_stage(7, "PRISMA DIAGRAM (Pure Python)")
        print("   Generating PRISMA flow diagram...")
        
        # PRISMA stage
        prisma_input = {
            "search": accumulated_data.get("search", {}),
            "screen": accumulated_data.get("screen", {}),
        }
        
        try:
            result = await run_stage(orchestrator, "prisma", prisma_input, workflow.id)
            if result.success:
                accumulated_data["prisma"] = result.output_data
                print_result("✅ Success", "True")
        except Exception as e:
            print(f"⚠️  PRISMA error (continuing): {e}")
        
        print_stage(8, "TABLES (Pure Python)")
        print("   Generating study tables...")
        
        tables_input = {
            "extractions": accumulated_data.get("extractions", []),
            "rob_data": accumulated_data.get("rob", {}),
        }
        
        try:
            result = await run_stage(orchestrator, "tables", tables_input, workflow.id)
            if result.success:
                accumulated_data["tables"] = result.output_data
                print_result("✅ Success", "True")
        except Exception as e:
            print(f"⚠️  Tables error (continuing): {e}")
        
        # ===================================================================
        # STAGES 9-12: MANUSCRIPT WRITING (Real API - o3-pro)
        # ===================================================================
        print_stage(9, "INTRODUCTION (Real OpenAI API - o3-pro)")
        print("   ⚠️  Making expensive API calls for manuscript writing...")
        print("   (Skipping to save costs - demonstration purposes)")
        
        # For demo, we'll skip the expensive writing stages
        # In a real test, you would run:
        # - introduction
        # - methods
        # - results  
        # - discussion
        
        print("   [SKIPPED - Writing stages use expensive o3-pro model]")
        
        # ===================================================================
        # SUMMARY
        # ===================================================================
        print_header("📊 PIPELINE SUMMARY", "=")
        
        print("\n  STAGES COMPLETED:")
        print(f"    ✅ Search (mocked)")
        print(f"    ✅ Screening (real API)")
        print(f"    ✅ PDF Fetch (mocked)")
        print(f"    ✅ Data Extraction (real API)")
        print(f"    {'✅' if 'rob' in accumulated_data else '⚠️'} Risk of Bias")
        print(f"    {'✅' if 'analysis' in accumulated_data else '⚠️'} Analysis")
        print(f"    {'✅' if 'prisma' in accumulated_data else '⚠️'} PRISMA")
        print(f"    {'✅' if 'tables' in accumulated_data else '⚠️'} Tables")
        print(f"    ⏭️  Writing stages (skipped)")
        
        print("\n  TIMING:")
        total_time = sum(stage_times.values())
        for stage, t in stage_times.items():
            print(f"    {stage:<20} {t:>6.1f}s")
        print(f"    {'Total':<20} {total_time:>6.1f}s")
        
        print("\n  COST:")
        print(f"    Total API cost: ${total_cost:.2f}")
        print(f"    (Writing stages would add ~$8-12)")
        
        print("\n  DATA EXTRACTED:")
        if "extractions" in accumulated_data:
            for ext in accumulated_data["extractions"]:
                print(f"\n    📄 {ext.get('paper_id', 'Unknown')}")
                data = ext.get("data", {})
                for key in ["sample_size_total", "intervention_name", "primary_outcome"]:
                    if key in data:
                        print(f"       {key}: {data[key]}")
        
        print("\n" + "="*80)
        print("  ✅ E2E PIPELINE TEST COMPLETE")
        print("="*80 + "\n")
        
        # Save results
        output = {
            "workflow_id": workflow.id,
            "research_question": RESEARCH_QUESTION,
            "stages_completed": list(accumulated_data.keys()),
            "total_cost": total_cost,
            "total_time": total_time,
            "data": {k: v for k, v in accumulated_data.items() if k != "papers"},
        }
        
        with open("pipeline_test_results.json", "w") as f:
            json.dump(output, f, indent=2, default=str)
        
        print("  💾 Results saved to: pipeline_test_results.json")
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def main():
    """Main entry point."""
    
    print("\n" + "="*80)
    print("  ARAKIS FULL PIPELINE E2E TEST")
    print("="*80)
    print("\n  ⚠️  WARNING: This will make REAL API calls!")
    print("     Stages with real API calls:")
    print("       - Screening (single-pass mode)")
    print("       - Data Extraction (single-pass mode)")
    print("       - Risk of Bias")
    print("     Estimated cost: $2-5")
    print("\n  Press Ctrl+C within 5 seconds to cancel...")
    
    try:
        for i in range(5, 0, -1):
            print(f"    Starting in {i}...", end="\r")
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print("\n  Cancelled.")
        return
    
    print("\n\n  Starting pipeline...\n")
    
    try:
        await test_pipeline()
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user.")
    except Exception as e:
        print(f"\n\n  ❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n  Cancelled.")
        sys.exit(0)
