from __future__ import annotations

"""Search orchestrator - coordinates multi-database searches."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from arakis.agents.query_generator import QueryGeneratorAgent
from arakis.clients.base import BaseSearchClient, RateLimitError, SearchClientError
from arakis.clients.google_scholar import GoogleScholarClient
from arakis.clients.openalex import OpenAlexClient
from arakis.clients.pubmed import PubMedClient
from arakis.clients.semantic_scholar import SemanticScholarClient
from arakis.deduplication import DeduplicationResult, Deduplicator
from arakis.models.paper import Paper, PRISMAFlow, SearchResult


@dataclass
class ComprehensiveSearchResult:
    """Result of a comprehensive multi-database search."""

    research_question: str
    papers: list[Paper]
    prisma_flow: PRISMAFlow

    # Query tracking
    queries_generated: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    queries_executed: int = 0

    # Search metadata
    databases_searched: list[str] = field(default_factory=list)
    search_started: datetime = field(default_factory=datetime.utcnow)
    search_completed: datetime | None = None
    total_execution_time_ms: int = 0

    # Deduplication info
    dedup_result: DeduplicationResult | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "research_question": self.research_question,
            "paper_count": len(self.papers),
            "databases": self.databases_searched,
            "queries_executed": self.queries_executed,
            "prisma_flow": {
                "identified": self.prisma_flow.total_identified,
                "duplicates_removed": self.prisma_flow.duplicates_removed,
                "after_dedup": self.prisma_flow.after_dedup,
            },
            "execution_time_ms": self.total_execution_time_ms,
        }


class SearchOrchestrator:
    """
    Orchestrates comprehensive literature searches across multiple databases.

    Features:
    - LLM-powered query generation
    - Parallel multi-database search
    - Automatic deduplication
    - PRISMA flow tracking
    """

    def __init__(self):
        self.query_agent = QueryGeneratorAgent()
        self.deduplicator = Deduplicator()

        # Initialize all available clients
        self._clients: dict[str, BaseSearchClient] = {
            "pubmed": PubMedClient(),
            "openalex": OpenAlexClient(),
            "semantic_scholar": SemanticScholarClient(),
            "google_scholar": GoogleScholarClient(),
        }

    @property
    def available_databases(self) -> list[str]:
        """List of available database names."""
        return list(self._clients.keys())

    async def comprehensive_search(
        self,
        research_question: str,
        databases: list[str] | None = None,
        queries_per_database: int = 3,
        max_results_per_query: int = 500,
        validate_queries: bool = True,
        progress_callback: Callable | None = None,
    ) -> ComprehensiveSearchResult:
        """
        Execute a comprehensive multi-database search.

        Args:
            research_question: The research question to search for
            databases: List of databases to search (default: pubmed, openalex, semantic_scholar)
            queries_per_database: Number of query variations per database
            max_results_per_query: Maximum results per query
            validate_queries: Whether to validate queries before full execution
            progress_callback: Optional callback(stage, detail) for progress updates

        Returns:
            ComprehensiveSearchResult with papers and metadata
        """
        start_time = datetime.utcnow()

        # Default databases (excluding Google Scholar due to rate limits)
        if databases is None:
            databases = ["pubmed", "openalex", "semantic_scholar"]

        # Filter to available databases
        databases = [db for db in databases if db in self._clients]

        if progress_callback:
            progress_callback(
                "generating_queries", f"Generating queries for {len(databases)} databases"
            )

        # Step 1: Generate optimized queries
        queries = await self.query_agent.generate_queries(
            research_question,
            databases,
            queries_per_database,
        )

        # Step 2: Optionally validate queries
        if validate_queries:
            if progress_callback:
                progress_callback("validating_queries", "Validating query result counts")
            queries = await self._validate_and_refine_queries(queries)

        if progress_callback:
            progress_callback("executing_searches", f"Searching {len(databases)} databases")

        # Step 3: Execute searches
        all_results: list[SearchResult] = []
        queries_executed = 0

        for db_name, query_list in queries.items():
            if db_name not in self._clients:
                continue

            client = self._clients[db_name]

            for query_info in query_list:
                query = query_info.get("query", "")
                if not query:
                    continue

                try:
                    result = await client.search(query, max_results_per_query)
                    all_results.append(result)
                    queries_executed += 1

                    if progress_callback:
                        progress_callback(
                            "search_complete",
                            f"{db_name}: {result.count} papers ({result.total_available} available)",
                        )
                except (RateLimitError, SearchClientError) as e:
                    # For rate limit errors, warn but continue with partial results
                    if "rate limit" in str(e).lower() or isinstance(e, RateLimitError):
                        if progress_callback:
                            progress_callback(
                                "search_warning",
                                f"{db_name}: Rate limit reached, skipping remaining queries",
                            )
                        break  # Skip remaining queries for this database
                    else:
                        if progress_callback:
                            progress_callback("search_error", f"{db_name}: {e}")
                    continue
                except Exception as e:
                    # Catch tenacity.RetryError and other unexpected errors
                    if "rate limit" in str(e).lower() or "retryerror" in type(e).__name__.lower():
                        if progress_callback:
                            progress_callback(
                                "search_warning",
                                f"{db_name}: Rate limit reached, skipping remaining queries",
                            )
                        break
                    else:
                        if progress_callback:
                            progress_callback("search_error", f"{db_name}: {type(e).__name__}: {e}")
                        continue

        # Step 4: Collect all papers
        all_papers = []
        records_per_db: dict[str, int] = {}

        for result in all_results:
            all_papers.extend(result.papers)
            db_name = result.source.value
            records_per_db[db_name] = records_per_db.get(db_name, 0) + len(result.papers)

        if progress_callback:
            progress_callback("deduplicating", f"Deduplicating {len(all_papers)} papers")

        # Step 5: Deduplicate
        dedup_result = self.deduplicator.deduplicate(all_papers)

        # Step 6: Build PRISMA flow
        prisma_flow = PRISMAFlow(
            records_identified=records_per_db,
            duplicates_removed=dedup_result.duplicates_removed,
        )

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = int((end_time - start_time).total_seconds() * 1000)

        result = ComprehensiveSearchResult(
            research_question=research_question,
            papers=dedup_result.unique_papers,
            prisma_flow=prisma_flow,
            queries_generated=queries,
            queries_executed=queries_executed,
            databases_searched=databases,
            search_started=start_time,
            search_completed=end_time,
            total_execution_time_ms=execution_time,
            dedup_result=dedup_result,
        )

        if progress_callback:
            progress_callback(
                "complete",
                f"Found {len(result.papers)} unique papers from {result.prisma_flow.total_identified} total",
            )

        return result

    async def _validate_and_refine_queries(
        self,
        queries: dict[str, list[dict[str, str]]],
        target_range: tuple[int, int] = (50, 5000),
    ) -> dict[str, list[dict[str, str]]]:
        """Validate queries and refine those with extreme result counts."""
        validated = await self.query_agent.validate_queries(queries)

        refined = {}
        for db_name, query_list in validated.items():
            refined[db_name] = []

            for query_info in query_list:
                if not query_info.get("valid", True):
                    # Skip invalid queries
                    continue

                count = query_info.get("result_count", 0)
                min_results, max_results = target_range

                if count < min_results or count > max_results:
                    # Try to refine
                    try:
                        refined_query = await self.query_agent.refine_query(
                            db_name, query_info["query"], count, target_range
                        )
                        refined[db_name].append(refined_query)
                    except Exception:
                        # Keep original if refinement fails
                        refined[db_name].append(query_info)
                else:
                    refined[db_name].append(query_info)

        return refined

    async def search_single_database(
        self,
        query: str,
        database: str,
        max_results: int = 100,
    ) -> SearchResult:
        """
        Execute a direct search on a single database.

        Args:
            query: The search query
            database: Database name
            max_results: Maximum results

        Returns:
            SearchResult
        """
        if database not in self._clients:
            raise ValueError(f"Unknown database: {database}. Available: {self.available_databases}")

        client = self._clients[database]
        return await client.search(query, max_results)
