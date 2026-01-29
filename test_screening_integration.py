#!/usr/bin/env python3
"""
Integration test for the screening workflow.

This test:
1. Creates a real workflow in the database
2. Mocks external API calls (OpenAI, PubMed, OpenAlex)
3. Runs the complete search + screening pipeline
4. Verifies the results
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.insert(0, "src")

from arakis.config import Settings
from arakis.database.models import Base, Workflow, Paper, ScreeningDecision
from arakis.workflow.stages.search import SearchStageExecutor
from arakis.workflow.stages.screen import ScreenStageExecutor
from arakis.workflow.stages.base import StageResult


# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_screening.db"


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        # Cleanup
        await session.rollback()
    
    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
def mock_openai_responses():
    """Create mock OpenAI API responses for screening."""
    
    def create_screening_response(decision="INCLUDE", confidence=0.92, reason="Meets criteria"):
        return {
            "id": f"chatcmpl-{uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now(timezone.utc).timestamp()),
            "model": "gpt-4o",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{uuid4().hex[:8]}",
                        "type": "function",
                        "function": {
                            "name": "screen_paper",
                            "arguments": json.dumps({
                                "decision": decision,
                                "confidence": confidence,
                                "reason": reason,
                                "matched_inclusion": ["Human RCTs", "Sepsis patients"],
                                "matched_exclusion": []
                            })
                        }
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {
                "prompt_tokens": 450,
                "completion_tokens": 85,
                "total_tokens": 535
            }
        }
    
    # Create responses for 10 papers
    # Papers 0-4: INCLUDE (both passes agree)
    # Paper 5: CONFLICT (pass1=INCLUDE, pass2=MAYBE)
    # Papers 6-9: EXCLUDE (both passes agree)
    
    responses = []
    
    for i in range(10):
        if i < 5:
            # INCLUDE
            responses.append(create_screening_response("INCLUDE", 0.92, f"RCT with sepsis patients (paper {i})"))
        elif i == 5:
            # CONFLICT - first pass INCLUDE
            responses.append(create_screening_response("INCLUDE", 0.88, f"Looks like RCT (paper {i})"))
        elif i == 5:
            # CONFLICT - second pass MAYBE (will be handled separately)
            pass
        else:
            # EXCLUDE
            responses.append(create_screening_response("EXCLUDE", 0.95, f"Animal study (paper {i})"))
    
    # Add conflict second pass
    responses.insert(11, create_screening_response("MAYBE", 0.65, "Unclear if human study"))
    
    return responses


@pytest.fixture
def sample_search_results():
    """Create sample search results."""
    return {
        "papers_found": 10,
        "duplicates_removed": 3,
        "records_identified": {"pubmed": 8, "openalex": 5},
        "papers": [
            {
                "id": f"pubmed_{38012340 + i}",
                "title": f"Aspirin and sepsis mortality study {i+1}",
                "abstract": f"Background: Aspirin may improve sepsis outcomes. Methods: RCT with {100+i*10} patients. Results: Mortality reduced.",
                "year": 2020 + i,
                "source": "pubmed",
                "doi": f"10.1234/paper{i+1}",
                "pmid": str(38012340 + i),
                "authors": [{"name": f"Author {i+1}"}, {"name": f"CoAuthor {i+1}"}],
                "journal": "Critical Care Medicine",
            }
            for i in range(10)
        ]
    }


class TestScreeningWorkflow:
    """Integration tests for the screening workflow."""
    
    @pytest.mark.asyncio
    async def test_screen_stage_executor_initialization(self, db_session):
        """Test that ScreenStageExecutor can be initialized."""
        workflow_id = str(uuid4())
        
        executor = ScreenStageExecutor(workflow_id, db_session)
        
        assert executor.STAGE_NAME == "screen"
        assert executor.workflow_id == workflow_id
        assert executor.screener is not None
    
    @pytest.mark.asyncio
    async def test_screen_stage_requires_search(self, db_session):
        """Test that screen stage requires search to be completed first."""
        workflow_id = str(uuid4())
        executor = ScreenStageExecutor(workflow_id, db_session)
        
        required = executor.get_required_stages()
        
        assert "search" in required
    
    @pytest.mark.asyncio
    async def test_screen_stage_validates_input(self, db_session):
        """Test that screen stage validates input data."""
        workflow_id = str(uuid4())
        executor = ScreenStageExecutor(workflow_id, db_session)
        
        # Test with no papers
        result = await executor.execute({
            "papers": [],
            "inclusion_criteria": ["Human RCTs"],
        })
        
        assert result.success is False
        assert "No papers" in result.error
        
        # Test with no criteria
        result = await executor.execute({
            "papers": [{"id": "test", "title": "Test"}],
            "inclusion_criteria": [],
        })
        
        assert result.success is False
        assert "inclusion_criteria" in result.error
    
    @pytest.mark.asyncio
    async def test_screen_stage_with_mocked_openai(self, db_session, sample_search_results):
        """Test complete screening stage with mocked OpenAI API."""
        workflow_id = str(uuid4())
        
        # Create workflow in database
        workflow = Workflow(
            id=workflow_id,
            research_question="Effect of aspirin on sepsis mortality",
            inclusion_criteria="Human RCTs, Sepsis patients",
            exclusion_criteria="Animal studies, Reviews",
            databases=["pubmed", "openalex"],
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(workflow)
        await db_session.commit()
        
        executor = ScreenStageExecutor(workflow_id, db_session)
        
        # Mock OpenAI responses
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            # Create mock response
            mock_response = MagicMock()
            mock_response.id = f"chatcmpl-{uuid4()}"
            
            # Determine decision based on call number
            # Each paper gets 2 calls (dual-review)
            paper_index = (call_count - 1) // 2
            is_second_pass = (call_count - 1) % 2 == 1
            
            if paper_index < 5:
                decision = "INCLUDE"
                confidence = 0.92 if not is_second_pass else 0.88
                reason = f"RCT with sepsis (paper {paper_index}, pass {2 if is_second_pass else 1})"
            elif paper_index == 5 and is_second_pass:
                # Conflict case
                decision = "MAYBE"
                confidence = 0.65
                reason = "Unclear population"
            elif paper_index == 5:
                decision = "INCLUDE"
                confidence = 0.88
                reason = "Looks like RCT"
            else:
                decision = "EXCLUDE"
                confidence = 0.95
                reason = f"Animal study (paper {paper_index})"
            
            # Create proper mock structure
            mock_choice = MagicMock()
            mock_message = MagicMock()
            
            mock_tool_call = MagicMock()
            mock_tool_call.id = f"call_{uuid4().hex[:8]}"
            mock_tool_call.type = "function"
            
            mock_function = MagicMock()
            mock_function.name = "screen_paper"
            mock_function.arguments = json.dumps({
                "decision": decision,
                "confidence": confidence,
                "reason": reason,
                "matched_inclusion": ["Human RCTs", "Sepsis patients"] if decision == "INCLUDE" else [],
                "matched_exclusion": ["Animal studies"] if decision == "EXCLUDE" else []
            })
            
            mock_tool_call.function = mock_function
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            return mock_response
        
        with patch.object(executor.screener.client.chat.completions, 'create', side_effect=mock_create):
            result = await executor.execute({
                "papers": sample_search_results["papers"],
                "inclusion_criteria": ["Human RCTs", "Sepsis patients", "Mortality outcome"],
                "exclusion_criteria": ["Animal studies", "Reviews", "Case reports"],
                "fast_mode": False,
            })
        
        # Verify result
        assert result.success is True, f"Screening failed: {result.error}"
        assert result.output_data["total_screened"] == 10
        assert result.cost > 0
        
        # Verify decisions
        decisions = result.output_data["decisions"]
        assert len(decisions) == 10
        
        # Check that we got expected counts
        # Note: decisions can be dict or ScreeningDecision object depending on serialization
        def get_status(d):
            status = d.get("status") if isinstance(d, dict) else str(d.status)
            return status.lower() if isinstance(status, str) else str(status).lower()
        
        included = sum(1 for d in decisions if "include" in get_status(d))
        excluded = sum(1 for d in decisions if "exclude" in get_status(d))
        maybe = sum(1 for d in decisions if "maybe" in get_status(d))
        
        # Verify we have the expected distribution
        assert included + excluded + maybe == 10
        assert included > 0  # Should have some included
        assert result.output_data["conflicts"] > 0  # Should have at least one conflict
        
        # Verify conflict was detected (at least 1 conflict from paper 5)
        conflict_decisions = [d for d in decisions if d.get("is_conflict") or d.get("is_conflict") is True]
        assert len(conflict_decisions) >= 1, "Expected at least one conflict"
        
        # The conflict should have been resolved to MAYBE
        conflict_maybe = [d for d in conflict_decisions if "maybe" in get_status(d)]
        assert len(conflict_maybe) >= 1, "Expected at least one MAYBE from conflict"
        
        # Verify workflow was updated
        await db_session.refresh(workflow)
        assert workflow.papers_screened == 10
        assert workflow.papers_included == 5
        
        print(f"\n✅ Screening completed successfully!")
        print(f"   Total screened: {result.output_data['total_screened']}")
        print(f"   Included: {result.output_data['included']}")
        print(f"   Excluded: {result.output_data['excluded']}")
        print(f"   Maybe: {result.output_data['maybe']}")
        print(f"   Conflicts: {result.output_data['conflicts']}")
        print(f"   Cost: ${result.cost:.2f}")
        print(f"   API calls: {call_count}")
    
    @pytest.mark.asyncio
    async def test_screen_stage_fast_mode(self, db_session, sample_search_results):
        """Test screening in fast mode (single pass)."""
        workflow_id = str(uuid4())
        
        # Create workflow
        workflow = Workflow(
            id=workflow_id,
            research_question="Effect of aspirin on sepsis mortality",
            inclusion_criteria="Human RCTs",
            exclusion_criteria="Animal studies",
            databases=["pubmed"],
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(workflow)
        await db_session.commit()
        
        executor = ScreenStageExecutor(workflow_id, db_session)
        
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            
            mock_tool_call = MagicMock()
            mock_function = MagicMock()
            mock_function.name = "screen_paper"
            mock_function.arguments = json.dumps({
                "decision": "INCLUDE" if call_count <= 5 else "EXCLUDE",
                "confidence": 0.90,
                "reason": "Fast mode screening",
                "matched_inclusion": [],
                "matched_exclusion": []
            })
            mock_tool_call.function = mock_function
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            return mock_response
        
        with patch.object(executor.screener.client.chat.completions, 'create', side_effect=mock_create):
            result = await executor.execute({
                "papers": sample_search_results["papers"],
                "inclusion_criteria": ["Human RCTs"],
                "exclusion_criteria": ["Animal studies"],
                "fast_mode": True,  # Single pass
            })
        
        assert result.success is True
        # Fast mode = 1 call per paper = 10 calls
        assert call_count == 10
        # Cost should be lower (half of dual-review)
        assert result.cost < 0.30  # 10 papers × $0.02 = $0.20
    
    @pytest.mark.asyncio
    async def test_full_search_to_screen_pipeline(self, db_session):
        """Test complete pipeline from search to screening."""
        workflow_id = str(uuid4())
        
        # Create workflow
        workflow = Workflow(
            id=workflow_id,
            research_question="Effect of aspirin on sepsis mortality",
            inclusion_criteria="Human RCTs, Sepsis patients",
            exclusion_criteria="Animal studies, Reviews",
            databases=["pubmed", "openalex"],
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(workflow)
        await db_session.commit()
        
        # Step 1: Search Stage
        search_executor = SearchStageExecutor(workflow_id, db_session)
        
        # Mock search orchestrator
        mock_search_result = MagicMock()
        mock_search_result.papers = [
            MagicMock(
                id=f"pubmed_{38012340 + i}",
                title=f"Study {i+1}",
                abstract="RCT with sepsis patients",
                year=2023,
                source=MagicMock(value="pubmed"),
                doi=f"10.1234/{i}",
                pmid=str(38012340 + i),
                authors=[MagicMock(name=f"Author {i}")],
            )
            for i in range(5)
        ]
        mock_search_result.prisma_flow = MagicMock(
            duplicates_removed=2,
            records_identified={"pubmed": 5, "openalex": 2},
        )
        
        with patch.object(
            search_executor.orchestrator,
            'comprehensive_search',
            new_callable=AsyncMock,
            return_value=mock_search_result
        ):
            search_result = await search_executor.execute({
                "research_question": "Effect of aspirin on sepsis mortality",
                "databases": ["pubmed", "openalex"],
            })
        
        assert search_result.success is True
        assert search_result.output_data["papers_found"] == 5
        
        # Step 2: Screen Stage
        screen_executor = ScreenStageExecutor(workflow_id, db_session)
        
        call_count = 0
        async def mock_screen_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            
            mock_tool_call = MagicMock()
            mock_function = MagicMock()
            mock_function.name = "screen_paper"
            mock_function.arguments = json.dumps({
                "decision": "INCLUDE",
                "confidence": 0.92,
                "reason": "RCT with sepsis",
                "matched_inclusion": ["Human RCTs"],
                "matched_exclusion": []
            })
            mock_tool_call.function = mock_function
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            return mock_response
        
        with patch.object(screen_executor.screener.client.chat.completions, 'create', side_effect=mock_screen_create):
            screen_result = await screen_executor.execute({
                "papers": search_result.output_data["papers"],
                "inclusion_criteria": ["Human RCTs"],
                "exclusion_criteria": ["Animal studies"],
                "fast_mode": True,
            })
        
        assert screen_result.success is True
        assert screen_result.output_data["total_screened"] == 5
        assert screen_result.output_data["included"] == 5
        
        print(f"\n✅ Full pipeline test passed!")
        print(f"   Search: {search_result.output_data['papers_found']} papers found")
        print(f"   Screen: {screen_result.output_data['included']} papers included")
        print(f"   Total API calls: {call_count}")


async def run_manual_test():
    """Run a manual test without pytest."""
    print("="*80)
    print("ARKIS SCREENING WORKFLOW - INTEGRATION TEST")
    print("="*80)
    
    # Create engine and session
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        workflow_id = str(uuid4())
        
        print(f"\n1. Creating workflow: {workflow_id}")
        
        workflow = Workflow(
            id=workflow_id,
            research_question="Effect of aspirin on sepsis mortality",
            inclusion_criteria="Human RCTs, Sepsis patients, Mortality outcome",
            exclusion_criteria="Animal studies, Reviews, Case reports",
            databases=["pubmed", "openalex"],
            status="running",
            created_at=datetime.now(timezone.utc),
        )
        session.add(workflow)
        await session.commit()
        print("   ✅ Workflow created")
        
        # Create executor
        print("\n2. Initializing ScreenStageExecutor")
        executor = ScreenStageExecutor(workflow_id, session)
        print("   ✅ Executor initialized")
        
        # Sample papers
        papers = [
            {
                "id": f"pubmed_{38012340 + i}",
                "title": f"Aspirin and sepsis mortality: RCT {i+1}",
                "abstract": f"Background: Sepsis is a major cause of mortality. Methods: Double-blind RCT with {100+i*20} sepsis patients. Results: Aspirin reduced 28-day mortality by 25% (p=0.03).",
                "year": 2020 + i,
                "source": "pubmed",
                "doi": f"10.1234/paper{i+1}",
                "pmid": str(38012340 + i),
                "authors": [{"name": f"Smith J"}, {"name": f"Jones M"}],
            }
            for i in range(5)
        ]
        print(f"\n3. Prepared {len(papers)} papers for screening")
        
        # Mock OpenAI
        print("\n4. Running screening with mocked OpenAI API")
        print("   (Each paper gets 2 API calls for dual-review mode)")
        
        call_count = 0
        
        async def mock_create(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            paper_idx = (call_count - 1) // 2
            is_second = (call_count - 1) % 2 == 1
            
            # Simulate one conflict on paper 2
            if paper_idx == 2 and is_second:
                decision = "MAYBE"
                confidence = 0.65
                reason = "Unclear if severe sepsis criteria met"
            else:
                decision = "INCLUDE"
                confidence = 0.92 if not is_second else 0.88
                reason = f"RCT with sepsis patients and mortality outcome (call {call_count})"
            
            # Create proper mock structure matching OpenAI client
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_message = MagicMock()
            
            # tool_calls needs to be a list of objects with .function attribute
            mock_tool_call = MagicMock()
            mock_tool_call.id = f"call_{call_count}"
            mock_tool_call.type = "function"
            
            mock_function = MagicMock()
            mock_function.name = "screen_paper"
            mock_function.arguments = json.dumps({
                "decision": decision,
                "confidence": confidence,
                "reason": reason,
                "matched_inclusion": ["Human RCTs", "Sepsis patients", "Mortality outcome"],
                "matched_exclusion": []
            })
            
            mock_tool_call.function = mock_function
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            return mock_response
        
        with patch.object(executor.screener.client.chat.completions, 'create', side_effect=mock_create):
            start_time = datetime.now()
            result = await executor.execute({
                "papers": papers,
                "inclusion_criteria": ["Human RCTs", "Sepsis patients", "Mortality outcome"],
                "exclusion_criteria": ["Animal studies", "Reviews", "Case reports"],
                "fast_mode": False,
            })
            duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n5. Results:")
        print(f"   ✅ Success: {result.success}")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        print(f"   📊 Total screened: {result.output_data['total_screened']}")
        print(f"   ✅ Included: {result.output_data['included']}")
        print(f"   ❌ Excluded: {result.output_data['excluded']}")
        print(f"   ⚠️  Maybe: {result.output_data['maybe']}")
        print(f"   🔥 Conflicts: {result.output_data['conflicts']}")
        print(f"   💰 Cost: ${result.cost:.2f}")
        print(f"   📡 API calls: {call_count}")
        
        # Verify database state
        await session.refresh(workflow)
        print(f"\n6. Database state:")
        print(f"   📄 papers_screened: {workflow.papers_screened}")
        print(f"   ✅ papers_included: {workflow.papers_included}")
        
        # Show sample decisions
        print(f"\n7. Sample decisions:")
        for i, decision in enumerate(result.output_data['decisions'][:3]):
            print(f"   Paper {i+1}: {decision['status']} (confidence: {decision['confidence']:.2f})")
            print(f"      Reason: {decision['reason'][:60]}...")
            if decision['is_conflict']:
                print(f"      ⚠️  CONFLICT DETECTED")
        
        print("\n" + "="*80)
        print("TEST COMPLETED SUCCESSFULLY")
        print("="*80)
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    
    return result


if __name__ == "__main__":
    # Run manual test
    asyncio.run(run_manual_test())
