"""LLM-powered query generator using OpenAI GPT with tool functions."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from arakis.clients.base import BaseSearchClient
from arakis.clients.google_scholar import GoogleScholarClient
from arakis.clients.openalex import OpenAlexClient
from arakis.clients.pubmed import PubMedClient
from arakis.clients.semantic_scholar import SemanticScholarClient
from arakis.config import get_settings
from arakis.utils import retry_with_exponential_backoff

# Tool function definitions for GPT
QUERY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_pubmed_query",
            "description": "Generate a PubMed search query using MeSH terms and Boolean operators",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The complete PubMed query with MeSH terms, field tags, and Boolean operators",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the query strategy",
                    },
                },
                "required": ["query", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_openalex_query",
            "description": "Generate an OpenAlex search query (text search or filter syntax)",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The OpenAlex query (simple text or filter syntax)",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the query strategy",
                    },
                },
                "required": ["query", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_semantic_scholar_query",
            "description": "Generate a Semantic Scholar text search query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The Semantic Scholar search query"},
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the query strategy",
                    },
                },
                "required": ["query", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_google_scholar_query",
            "description": "Generate a Google Scholar search query with operators",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The Google Scholar query with optional operators",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Brief explanation of the query strategy",
                    },
                },
                "required": ["query", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_pico",
            "description": "Extract PICO components from a research question",
            "parameters": {
                "type": "object",
                "properties": {
                    "population": {
                        "type": "string",
                        "description": "Target population or patient group",
                    },
                    "intervention": {
                        "type": "string",
                        "description": "Treatment, exposure, or intervention being studied",
                    },
                    "comparison": {
                        "type": "string",
                        "description": "Comparison group or alternative (if applicable)",
                    },
                    "outcome": {"type": "string", "description": "Outcome being measured"},
                },
                "required": ["population", "intervention", "outcome"],
            },
        },
    },
]


class QueryGeneratorAgent:
    """
    LLM-powered agent for generating optimized search queries.

    Uses GPT with tool functions to generate database-specific queries
    that incorporate proper vocabulary (MeSH terms, etc.) and syntax.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.openai_model

        # Initialize search clients for query validation
        self._clients: dict[str, BaseSearchClient] = {
            "pubmed": PubMedClient(),
            "openalex": OpenAlexClient(),
            "semantic_scholar": SemanticScholarClient(),
            "google_scholar": GoogleScholarClient(),
        }

    def _get_system_prompt(self) -> str:
        """Generate system prompt with query syntax help from all clients."""
        syntax_guides = []
        for name, client in self._clients.items():
            syntax_guides.append(f"## {name.upper()}\n{client.get_query_syntax_help()}")

        return f"""You are an expert medical librarian and systematic review specialist.
Your task is to generate optimized search queries for academic databases.

You have access to the following databases and their query syntax:

{chr(10).join(syntax_guides)}

GUIDELINES:
1. For each database, generate queries that maximize recall while maintaining precision
2. Use controlled vocabulary (MeSH terms for PubMed) when available
3. Include synonyms and related terms
4. Consider truncation and phrase searching
5. For systematic reviews, err on the side of sensitivity (broader searches)

When generating queries:
- First extract PICO components from the research question
- Generate 2-3 query variations per database (narrow, medium, broad sensitivity)
- Explain your strategy for each query
"""

    @retry_with_exponential_backoff(max_retries=8, initial_delay=2.0, max_delay=90.0)
    async def _call_openai(self, messages: list[dict], tools: list | None = None):
        """
        Call OpenAI API with retry logic for rate limits.

        Args:
            messages: List of message dicts
            tools: Optional list of tool definitions

        Returns:
            OpenAI completion response
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        return await self.client.chat.completions.create(**kwargs)

    async def generate_queries(
        self,
        research_question: str,
        databases: list[str] | None = None,
        num_variations: int = 3,
    ) -> dict[str, list[dict[str, str]]]:
        """
        Generate optimized queries for each requested database.

        Args:
            research_question: The research question or topic
            databases: List of databases to generate queries for
            num_variations: Number of query variations per database

        Returns:
            Dict mapping database names to lists of {query, explanation} dicts
        """
        if databases is None:
            databases = ["pubmed", "openalex", "semantic_scholar"]

        # Filter to available clients
        databases = [db for db in databases if db in self._clients]

        # Build the user prompt
        user_prompt = f"""Research Question: {research_question}

Generate {num_variations} search query variations for each of these databases: {", ".join(databases)}

For each query:
1. First call extract_pico to identify the key components
2. Then generate queries for each database using the appropriate function
3. Vary the sensitivity: include at least one narrow (precise) and one broad (sensitive) query

Call the appropriate function for each query you generate."""

        # Call GPT with tools (with retry logic)
        response = await self._call_openai(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            tools=QUERY_TOOLS,
        )

        # Process tool calls
        results: dict[str, list[dict[str, str]]] = {db: [] for db in databases}
        pico: dict[str, str] = {}

        message = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                try:
                    args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    continue

                if func_name == "extract_pico":
                    pico = args
                elif func_name == "generate_pubmed_query" and "pubmed" in databases:
                    results["pubmed"].append(
                        {"query": args.get("query", ""), "explanation": args.get("explanation", "")}
                    )
                elif func_name == "generate_openalex_query" and "openalex" in databases:
                    results["openalex"].append(
                        {"query": args.get("query", ""), "explanation": args.get("explanation", "")}
                    )
                elif (
                    func_name == "generate_semantic_scholar_query"
                    and "semantic_scholar" in databases
                ):
                    results["semantic_scholar"].append(
                        {"query": args.get("query", ""), "explanation": args.get("explanation", "")}
                    )
                elif func_name == "generate_google_scholar_query" and "google_scholar" in databases:
                    results["google_scholar"].append(
                        {"query": args.get("query", ""), "explanation": args.get("explanation", "")}
                    )

        # If GPT didn't generate enough queries, request more
        for db in databases:
            if len(results[db]) < num_variations:
                additional = await self._generate_additional_queries(
                    research_question, db, num_variations - len(results[db]), pico
                )
                results[db].extend(additional)

        return results

    async def _generate_additional_queries(
        self, research_question: str, database: str, count: int, pico: dict[str, str]
    ) -> list[dict[str, str]]:
        """Generate additional queries for a specific database."""
        pico_context = ""
        if pico:
            pico_context = f"""
PICO components:
- Population: {pico.get("population", "N/A")}
- Intervention: {pico.get("intervention", "N/A")}
- Comparison: {pico.get("comparison", "N/A")}
- Outcome: {pico.get("outcome", "N/A")}
"""

        user_prompt = f"""Research Question: {research_question}
{pico_context}
Generate {count} more query variations for {database}.
Use the generate_{database}_query function for each query."""

        response = await self._call_openai(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            tools=QUERY_TOOLS,
        )

        results = []
        message = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                if database in func_name:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        results.append(
                            {
                                "query": args.get("query", ""),
                                "explanation": args.get("explanation", ""),
                            }
                        )
                    except json.JSONDecodeError:
                        continue

        return results

    async def validate_queries(
        self, queries: dict[str, list[dict[str, str]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Validate queries by executing them and checking result counts.

        Args:
            queries: Dict from generate_queries()

        Returns:
            Same structure with added 'valid', 'result_count', and 'error' fields
        """
        validated = {}

        for db_name, query_list in queries.items():
            if db_name not in self._clients:
                continue

            client = self._clients[db_name]
            validated[db_name] = []

            for query_info in query_list:
                query = query_info["query"]
                is_valid, count, error = await client.validate_query(query)

                validated[db_name].append(
                    {**query_info, "valid": is_valid, "result_count": count, "error": error}
                )

        return validated

    async def refine_query(
        self,
        database: str,
        original_query: str,
        result_count: int,
        target_range: tuple[int, int] = (50, 5000),
    ) -> dict[str, str]:
        """
        Refine a query that returns too many or too few results.

        Args:
            database: Target database
            original_query: The query to refine
            result_count: Current result count
            target_range: (min, max) desired result count

        Returns:
            Dict with refined query and explanation
        """
        min_results, max_results = target_range

        if result_count < min_results:
            direction = "broader (more sensitive)"
            action = "Add synonyms, remove restrictive terms, use broader MeSH terms"
        else:
            direction = "narrower (more specific)"
            action = "Add filters, use more specific terms, add required keywords"

        user_prompt = f"""The following {database} query returned {result_count} results.
Target range is {min_results}-{max_results} results.

Query: {original_query}

Make the query {direction}.
{action}

Generate a refined query using the generate_{database}_query function."""

        response = await self._call_openai(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": user_prompt},
            ],
            tools=QUERY_TOOLS,
        )

        message = response.choices[0].message

        if message.tool_calls:
            for tool_call in message.tool_calls:
                if database in tool_call.function.name:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        return {
                            "query": args.get("query", original_query),
                            "explanation": args.get("explanation", ""),
                        }
                    except json.JSONDecodeError:
                        pass

        return {"query": original_query, "explanation": "Could not refine query"}
