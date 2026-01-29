"""Data extraction agent using LLM with triple-review for reliability.

Supports cost mode configuration for quality/cost trade-offs.
"""

from __future__ import annotations

import json
import time
from typing import Any

from openai import AsyncOpenAI

from arakis.config import ModeConfig, get_default_mode_config, get_settings
from arakis.extraction.validator import validate_extraction
from arakis.logging import get_logger, log_failure, log_warning
from arakis.models.audit import AuditEventType
from arakis.models.extraction import (
    ExtractedData,
    ExtractionMethod,
    ExtractionResult,
    ExtractionSchema,
    ReviewerDecision,
)
from arakis.models.paper import Paper
from arakis.utils import BatchProcessor, retry_with_exponential_backoff

# Module logger
_logger = get_logger("extractor")

# Tool function definitions for LLM
EXTRACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "extract_data",
            "description": "Extract structured data from a paper based on the schema",
            "parameters": {
                "type": "object",
                "properties": {
                    "extractions": {
                        "type": "array",
                        "description": "List of extracted field values",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field_name": {
                                    "type": "string",
                                    "description": "Name of the field being extracted",
                                },
                                "value": {
                                    "description": "Extracted value (type depends on field type)"
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0,
                                    "maximum": 1,
                                    "description": "Confidence in this extraction (0-1)",
                                },
                                "reasoning": {
                                    "type": "string",
                                    "description": "Brief explanation of where/why this value was extracted",
                                },
                            },
                            "required": ["field_name", "value", "confidence"],
                        },
                    }
                },
                "required": ["extractions"],
            },
        },
    }
]


class DataExtractionAgent:
    """
    LLM-powered agent for extracting structured data from papers.

    Supports cost mode configuration for quality/cost trade-offs.
    
    QUALITY mode: Triple review (3 passes, gpt-5-mini)
    BALANCED/FAST/ECONOMY modes: Single pass (1 pass, gpt-5-nano)

    Features:
    - Triple-review mode: 3 independent passes with majority voting
    - Single-pass mode: 1 pass for speed (lower cost)
    - Confidence scoring based on reviewer agreement
    - Automatic conflict detection and resolution
    - Field validation against schema
    - Caching to avoid re-extraction
    """

    def __init__(self, mode_config: ModeConfig | None = None):
        """Initialize extraction agent.
        
        Args:
            mode_config: Cost mode configuration. If None, uses default (BALANCED).
        """
        self.settings = get_settings()
        self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        
        # Use mode config if provided, otherwise default
        self.mode_config = mode_config or get_default_mode_config()
        self.model = self.mode_config.extraction_model
        self.triple_review = self.mode_config.extraction_triple_review
        self.use_full_text = self.mode_config.use_full_text  # Always True
        
        self._extraction_cache: dict[str, ExtractedData] = {}  # Cache: paper_id+schema → extraction
        
        _logger.info(f"[extractor] Initialized with mode: {self.mode_config.name}, "
                    f"model: {self.model}, triple_review: {self.triple_review}")

    def _supports_temperature(self) -> bool:
        """Check if current model supports temperature parameter.
        
        o-series and gpt-5 models don't support temperature.
        """
        non_temp_models = ["o1", "o3", "o3-mini", "gpt-5", "gpt-5-mini", "gpt-5-nano"]
        return not any(self.model.startswith(m) for m in non_temp_models)

    @retry_with_exponential_backoff(max_retries=8, initial_delay=2.0, max_delay=90.0)
    async def _call_openai(
        self,
        messages: list[dict],
        tools: list | None = None,
        tool_choice: dict | str = "auto",
        temperature: float = 0.3,
    ):
        """
        Call OpenAI API with retry logic for rate limits.

        Args:
            messages: List of message dicts
            tools: Optional list of tool definitions
            tool_choice: Tool choice strategy or specific function
            temperature: Temperature for generation

        Returns:
            OpenAI completion response
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        
        # Only add temperature for models that support it
        if self._supports_temperature():
            kwargs["temperature"] = temperature
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return await self.client.chat.completions.create(**kwargs)

    def _get_system_prompt(self, schema: ExtractionSchema) -> str:
        """Generate system prompt for extraction."""
        # Build field descriptions
        field_descriptions = []
        for field in schema.fields:
            required_str = "REQUIRED" if field.required else "optional"
            validation = ""
            if field.validation_rules:
                rules = ", ".join(f"{k}={v}" for k, v in field.validation_rules.items())
                validation = f" (constraints: {rules})"

            field_descriptions.append(
                f"- **{field.name}** ({field.field_type.value}, {required_str}): "
                f"{field.description}{validation}"
            )

        fields_text = "\n".join(field_descriptions)

        return f"""You are an expert systematic reviewer extracting structured data from academic papers.

Your task is to carefully extract data according to the following schema:

**Schema: {schema.name}**
{schema.description}

**Fields to Extract:**
{fields_text}

**Extraction Guidelines:**

1. **Accuracy First**: Only extract data that is explicitly stated in the paper
2. **Be Conservative**: If information is unclear or missing, mark confidence as low (<0.5)
3. **Cite Location**: In reasoning, mention where you found the data (abstract, methods, results, table X, etc.)
4. **Handle Missing Data**:
   - Required fields: Extract even if uncertain (mark low confidence)
   - Optional fields: Omit if not found rather than guessing
5. **Type Consistency**:
   - NUMERIC: Extract only numbers (handle ranges by taking midpoint or noting both)
   - CATEGORICAL: Use exact values from allowed list if specified
   - TEXT: Keep concise, summarize if long
   - DATE: Use ISO format (YYYY-MM-DD) when possible
   - BOOLEAN: true/false
   - LIST: Array of items

6. **Confidence Scoring**:
   - 0.9-1.0: Explicitly stated with clear evidence
   - 0.7-0.9: Strongly implied or inferred from data
   - 0.5-0.7: Weakly implied, some uncertainty
   - 0.0-0.5: Guessing or very uncertain

Use the extract_data function to provide your extractions."""

    def _get_paper_text(self, paper: Paper, use_full_text: bool = False) -> str:
        """
        Format paper for extraction with intelligent full-text handling.

        Args:
            paper: Paper to extract from
            use_full_text: Whether to use full text if available

        Returns:
            Formatted text for LLM extraction
        """
        # Base metadata always included
        text_parts = [
            f"Title: {paper.title}",
            "\nMetadata:",
            f"- Year: {paper.year or 'Unknown'}",
            f"- Journal: {paper.journal or 'Unknown'}",
            f"- Authors: {paper.authors_string}",
            f"- Study Types: {', '.join(paper.publication_types) if paper.publication_types else 'Unknown'}",
        ]

        # Use full text if available and requested
        if use_full_text and paper.has_full_text:
            token_count = self._count_tokens(paper.full_text)

            # Truncate to 100K tokens for cost control (~$0.25 per paper input cost)
            if token_count > 100_000:
                text_parts.append(f"\n\nFull Text (truncated to 100K tokens from {token_count:,}):")
                text_parts.append(self._truncate_to_tokens(paper.full_text, 100_000))
                text_parts.append(
                    "\n[NOTE: Full text truncated for length. "
                    "Focus on extracting data from the sections provided.]"
                )
            else:
                text_parts.append(f"\n\nFull Text ({token_count:,} tokens):")
                text_parts.append(paper.full_text)
        else:
            # Fallback to abstract
            text_parts.append(f"\n\nAbstract: {paper.abstract or 'No abstract available'}")
            if use_full_text and not paper.has_full_text:
                text_parts.append(
                    "\n[NOTE: Full text was requested but not available. "
                    "Extraction based on abstract only. Be conservative with confidence scores.]"
                )

        return "\n".join(text_parts)

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens in

        Returns:
            Token count
        """
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        return len(encoding.encode(text))

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Truncate text to maximum token count.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens

        Returns:
            Truncated text
        """
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)

        if len(tokens) <= max_tokens:
            return text

        # Truncate and decode
        return encoding.decode(tokens[:max_tokens])

    async def _single_extraction_pass(
        self,
        paper: Paper,
        schema: ExtractionSchema,
        temperature: float = 0.3,
        reviewer_id: str = "reviewer1",
        use_full_text: bool = False,
    ) -> list[ReviewerDecision]:
        """
        Execute a single extraction pass.

        Returns list of ReviewerDecisions for each field.
        """
        paper_text = self._get_paper_text(paper, use_full_text=use_full_text)

        user_prompt = f"""Extract data from the following paper:

{paper_text}

Extract all fields defined in the schema. For each field, provide:
1. The extracted value
2. Your confidence (0-1)
3. Brief reasoning (where you found it)

Use the extract_data function."""

        response = await self._call_openai(
            messages=[
                {"role": "system", "content": self._get_system_prompt(schema)},
                {"role": "user", "content": user_prompt},
            ],
            tools=EXTRACTION_TOOLS,
            tool_choice={"type": "function", "function": {"name": "extract_data"}},
            temperature=temperature,
        )

        # Parse tool calls
        decisions = []
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            try:
                args = json.loads(tool_call.function.arguments)
                extractions = args.get("extractions", [])

                for extraction in extractions:
                    decisions.append(
                        ReviewerDecision(
                            field_name=extraction["field_name"],
                            value=extraction["value"],
                            confidence=extraction.get("confidence", 0.5),
                            reasoning=extraction.get("reasoning", ""),
                            reviewer_id=reviewer_id,
                        )
                    )
            except json.JSONDecodeError as e:
                log_failure(
                    _logger,
                    "Extraction response parsing",
                    e,
                    context={
                        "paper_id": paper.id,
                        "reviewer_id": reviewer_id,
                        "temperature": temperature,
                        "raw_arguments": tool_call.function.arguments[:200],
                    },
                )
            except KeyError as e:
                log_failure(
                    _logger,
                    "Extraction field parsing",
                    f"Missing required field: {e}",
                    context={
                        "paper_id": paper.id,
                        "reviewer_id": reviewer_id,
                        "temperature": temperature,
                    },
                )

        if not decisions:
            log_warning(
                _logger,
                "Extraction pass",
                "No extraction decisions returned from LLM",
                context={
                    "paper_id": paper.id,
                    "reviewer_id": reviewer_id,
                    "has_tool_calls": bool(message.tool_calls),
                },
            )

        return decisions

    def _resolve_conflicts(
        self, all_decisions: list[list[ReviewerDecision]], schema: ExtractionSchema
    ) -> tuple[dict[str, Any], dict[str, float], list[str]]:
        """
        Resolve conflicts between multiple reviewers using majority voting.

        Args:
            all_decisions: List of decision lists (one per reviewer)
            schema: Extraction schema

        Returns:
            Tuple of (final_data, confidence_scores, conflicts)
        """
        final_data: dict[str, Any] = {}
        confidence_scores: dict[str, float] = {}
        conflicts: list[str] = []

        # Group decisions by field
        decisions_by_field: dict[str, list[ReviewerDecision]] = {}
        for decisions in all_decisions:
            for decision in decisions:
                if decision.field_name not in decisions_by_field:
                    decisions_by_field[decision.field_name] = []
                decisions_by_field[decision.field_name].append(decision)

        # Resolve each field
        for field in schema.fields:
            field_decisions = decisions_by_field.get(field.name, [])

            if not field_decisions:
                # No reviewer extracted this field
                if field.required:
                    conflicts.append(f"{field.name}: No reviewer extracted (required field)")
                continue

            # For triple review: majority voting
            if len(field_decisions) >= 2:
                # Count occurrences of each value
                value_counts: dict[str, int] = {}
                value_to_decision: dict[str, ReviewerDecision] = {}

                for decision in field_decisions:
                    value_str = str(decision.value)
                    value_counts[value_str] = value_counts.get(value_str, 0) + 1
                    value_to_decision[value_str] = decision  # Keep one example

                # Find majority value
                max_count = max(value_counts.values())
                majority_values = [v for v, c in value_counts.items() if c == max_count]

                if len(majority_values) == 1:
                    # Clear majority
                    majority_value_str = majority_values[0]
                    majority_decision = value_to_decision[majority_value_str]
                    final_data[field.name] = majority_decision.value

                    # Confidence based on agreement
                    agreement_rate = max_count / len(field_decisions)
                    avg_confidence = (
                        sum(
                            d.confidence
                            for d in field_decisions
                            if str(d.value) == majority_value_str
                        )
                        / max_count
                    )
                    confidence_scores[field.name] = agreement_rate * avg_confidence

                    # Flag conflict if not unanimous
                    if max_count < len(field_decisions):
                        conflicts.append(
                            f"{field.name}: {max_count}/{len(field_decisions)} agreement"
                        )
                else:
                    # Tie - pick highest confidence
                    best_decision = max(field_decisions, key=lambda d: d.confidence)
                    final_data[field.name] = best_decision.value
                    confidence_scores[field.name] = (
                        best_decision.confidence * 0.5
                    )  # Reduce confidence for ties
                    conflicts.append(f"{field.name}: Tie between reviewers")
            else:
                # Single decision
                decision = field_decisions[0]
                final_data[field.name] = decision.value
                confidence_scores[field.name] = decision.confidence

        return final_data, confidence_scores, conflicts

    async def extract_paper(
        self,
        paper: Paper,
        schema: ExtractionSchema,
        triple_review: bool | None = None,
        use_full_text: bool | None = None,
    ) -> ExtractedData:
        """
        Extract data from a single paper.

        Args:
            paper: Paper to extract from
            schema: Extraction schema
            triple_review: Use triple-review (True) or single-pass (False).
                        If None (default), uses mode_config setting.
            use_full_text: Use full text if available. If None (default), uses mode_config.
                          Note: ALL modes use full text - this is always True.

        Returns:
            ExtractedData with extracted values and confidence scores
        """
        # Use mode_config settings if not explicitly overridden
        if triple_review is None:
            triple_review = self.triple_review
        if use_full_text is None:
            use_full_text = self.use_full_text
        start_time = time.time()

        # Ensure paper has audit trail
        trail = paper.ensure_audit_trail()

        # Check cache
        cache_key = f"{paper.id}_{schema.name}_{schema.version}_{use_full_text}"
        if cache_key in self._extraction_cache:
            return self._extraction_cache[cache_key]

        # Record extraction started
        trail.add_event(
            event_type=AuditEventType.EXTRACTION_STARTED,
            description="Data extraction process started",
            actor="DataExtractionAgent",
            details={
                "schema": schema.name,
                "triple_review": triple_review,
                "use_full_text": use_full_text,
                "model": self.model,
            },
            stage="extraction",
        )

        # Determine extraction method
        if triple_review:
            method = ExtractionMethod.TRIPLE_REVIEW
            temperatures = [0.2, 0.5, 0.8]  # Different temps for diversity
            reviewer_ids = ["reviewer1", "reviewer2", "reviewer3"]
        else:
            method = ExtractionMethod.SINGLE_PASS
            temperatures = [0.3]
            reviewer_ids = ["reviewer1"]

        # Execute extraction passes
        all_decisions = []
        all_reviewer_decisions = []

        for temp, reviewer_id in zip(temperatures, reviewer_ids):
            decisions = await self._single_extraction_pass(
                paper,
                schema,
                temperature=temp,
                reviewer_id=reviewer_id,
                use_full_text=use_full_text,
            )
            all_decisions.append(decisions)
            all_reviewer_decisions.extend(decisions)

            # Record each extraction pass
            trail.add_event(
                event_type=AuditEventType.EXTRACTION_PASS,
                description=f"Extraction pass by {reviewer_id}",
                actor="DataExtractionAgent",
                details={
                    "reviewer_id": reviewer_id,
                    "fields_extracted": len(decisions),
                    "avg_confidence": (
                        sum(d.confidence for d in decisions) / len(decisions) if decisions else 0
                    ),
                },
                stage="extraction",
                model_used=self.model,
                temperature=temp,
            )

        # Resolve conflicts and get final data
        final_data, confidence_scores, conflicts = self._resolve_conflicts(all_decisions, schema)

        # Record conflicts if any
        if conflicts:
            trail.add_event(
                event_type=AuditEventType.EXTRACTION_CONFLICT,
                description=f"{len(conflicts)} field(s) with conflicts detected",
                actor="DataExtractionAgent",
                details={
                    "conflict_count": len(conflicts),
                    "conflict_fields": conflicts,
                },
                stage="extraction",
            )

            trail.add_event(
                event_type=AuditEventType.EXTRACTION_RESOLVED,
                description="Conflicts resolved via majority voting",
                actor="DataExtractionAgent",
                details={
                    "resolution_method": "majority_voting",
                    "resolved_fields": list(final_data.keys()),
                },
                stage="extraction",
            )

        # Validate extracted data against schema constraints
        is_valid, field_errors = validate_extraction(schema, final_data, raise_on_error=False)
        validation_errors: list[str] = []
        invalid_fields: list[str] = []

        if not is_valid:
            for field_name, errors in field_errors.items():
                if field_name == "_unexpected":
                    # Unexpected fields are warnings, not critical errors
                    validation_errors.append(f"Warning: {'; '.join(errors)}")
                else:
                    invalid_fields.append(field_name)
                    validation_errors.append(f"{field_name}: {'; '.join(errors)}")

            # Add validation errors to conflicts list
            conflicts.extend(validation_errors)

            # Reduce confidence for invalid fields
            for field_name in invalid_fields:
                if field_name in confidence_scores:
                    # Halve confidence for fields that fail validation
                    confidence_scores[field_name] *= 0.5

            # Record validation failures in audit trail
            trail.add_event(
                event_type=AuditEventType.EXTRACTION_CONFLICT,
                description=f"Schema validation failed for {len(invalid_fields)} field(s)",
                actor="DataExtractionAgent",
                details={
                    "validation_errors": validation_errors,
                    "invalid_fields": invalid_fields,
                    "field_errors": field_errors,
                },
                stage="extraction",
            )

            _logger.warning(
                f"Schema validation failed for paper {paper.id}: {len(invalid_fields)} invalid fields"
            )

        # Calculate quality metrics
        extraction_quality = 1.0
        low_confidence_fields = [
            field_name
            for field_name, conf in confidence_scores.items()
            if conf < ExtractedData.LOW_CONFIDENCE_THRESHOLD
        ]

        # Reduce quality score for conflicts, validation errors, and low confidence
        if conflicts:
            extraction_quality -= 0.1 * len(conflicts) / len(schema.fields)
        if invalid_fields:
            # Additional penalty for schema validation failures (0.2 per invalid field)
            extraction_quality -= 0.2 * len(invalid_fields) / len(schema.fields)
        if low_confidence_fields:
            extraction_quality -= 0.15 * len(low_confidence_fields) / len(schema.fields)
        extraction_quality = max(0.0, extraction_quality)

        # Determine if needs review (include validation failures)
        needs_review = (
            len(conflicts) > 0
            or len(invalid_fields) > 0
            or len(low_confidence_fields) > 0
            or extraction_quality < 0.8
        )

        # Create result
        extraction_time_ms = int((time.time() - start_time) * 1000)

        extracted_data = ExtractedData(
            paper_id=paper.id,
            schema_name=schema.name,
            extraction_method=method,
            data=final_data,
            confidence=confidence_scores,
            reviewer_decisions=all_reviewer_decisions,
            conflicts=conflicts,
            low_confidence_fields=low_confidence_fields,
            extraction_quality=extraction_quality,
            extracted_by=f"DataExtractionAgent ({method.value})",
            extraction_time_ms=extraction_time_ms,
            needs_human_review=needs_review,
        )

        # Record extraction completed
        trail.add_event(
            event_type=AuditEventType.EXTRACTION_COMPLETED,
            description=f"Data extraction completed (quality: {extraction_quality:.2f})",
            actor="DataExtractionAgent",
            details={
                "fields_extracted": len(final_data),
                "extraction_quality": extraction_quality,
                "needs_human_review": needs_review,
                "conflict_count": len(conflicts),
                "validation_error_count": len(invalid_fields),
                "low_confidence_count": len(low_confidence_fields),
                "schema_validation_passed": is_valid,
            },
            stage="extraction",
            duration_ms=extraction_time_ms,
        )

        # Record if flagged for human review
        if needs_review:
            # Determine primary reason for review
            if len(invalid_fields) > 0:
                reason = "schema_validation_failed"
            elif extraction_quality < 0.8:
                reason = "quality_below_threshold"
            else:
                reason = "conflicts_or_low_confidence"

            trail.add_event(
                event_type=AuditEventType.EXTRACTION_HUMAN_REVIEW,
                description="Extraction flagged for human review",
                actor="DataExtractionAgent",
                details={
                    "reason": reason,
                    "conflicts": conflicts,
                    "invalid_fields": invalid_fields,
                    "low_confidence_fields": low_confidence_fields,
                },
                stage="extraction",
            )

        # Cache result
        self._extraction_cache[cache_key] = extracted_data

        return extracted_data

    async def extract_batch(
        self,
        papers: list[Paper],
        schema: ExtractionSchema,
        triple_review: bool | None = None,
        use_full_text: bool | None = None,
        progress_callback: callable = None,
        batch_size: int | None = None,
    ) -> ExtractionResult:
        """
        Extract data from multiple papers with configurable concurrent batch processing.

        Papers are processed concurrently within each batch to improve throughput
        while respecting API rate limits. Rate limiting is handled by the
        @retry_with_exponential_backoff decorator on individual API calls.

        Args:
            papers: List of papers to extract from
            schema: Extraction schema
            triple_review: Use triple-review mode. If None (default), uses mode_config.
            use_full_text: Use full text if available. If None (default), uses mode_config.
            progress_callback: Optional callback(current, total) for progress tracking.
                Note: For compatibility, this callback only receives (current, total).
            batch_size: Override the default batch size from settings.
                       If None, uses settings.batch_size_extraction (default: 3).

        Returns:
            ExtractionResult with all extractions and summary statistics
        """
        # Use mode_config settings if not explicitly overridden
        if triple_review is None:
            triple_review = self.triple_review
        if use_full_text is None:
            use_full_text = self.use_full_text
        
        start_time = time.time()

        # Use concurrent batch processing
        processor = BatchProcessor(
            batch_size=batch_size,
            batch_size_key="batch_size_extraction",
        )

        async def process_paper(paper: Paper) -> ExtractedData:
            return await self.extract_paper(paper, schema, triple_review, use_full_text)

        # Wrap the progress callback to match expected signature
        def wrapped_callback(
            current: int, total: int, paper: Paper, extraction: ExtractedData
        ) -> None:
            if progress_callback:
                progress_callback(current, total)

        extractions = await processor.process(papers, process_paper, wrapped_callback)

        total_time_ms = int((time.time() - start_time) * 1000)

        # Estimate cost (rough approximation)
        # Triple review: ~30K input tokens per paper, ~3K output
        # Single pass: ~10K input, ~1K output
        if triple_review:
            total_tokens_input = len(papers) * 30000
            total_tokens_output = len(papers) * 3000
        else:
            total_tokens_input = len(papers) * 10000
            total_tokens_output = len(papers) * 1000

        # GPT-4o pricing: $2.50/1M input, $10/1M output
        estimated_cost = (total_tokens_input * 2.50 / 1_000_000) + (
            total_tokens_output * 10 / 1_000_000
        )

        result = ExtractionResult(
            schema=schema,
            extractions=extractions,
            extraction_method=ExtractionMethod.TRIPLE_REVIEW
            if triple_review
            else ExtractionMethod.SINGLE_PASS,
            total_time_ms=total_time_ms,
            total_tokens_input=total_tokens_input,
            total_tokens_output=total_tokens_output,
            estimated_cost=estimated_cost,
        )

        return result

    def summarize_extraction(self, result: ExtractionResult) -> dict[str, Any]:
        """Generate summary statistics for extraction results."""
        return result.to_dict()
