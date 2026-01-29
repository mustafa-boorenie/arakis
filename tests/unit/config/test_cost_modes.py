"""Unit tests for cost mode configuration.
"""

import pytest

from arakis.config import (
    CostMode,
    ModeConfig,
    MODE_CONFIGS,
    get_mode_config,
    get_default_mode,
    get_default_mode_config,
    list_modes,
    validate_mode,
)


class TestCostMode:
    """Tests for CostMode enum."""

    def test_cost_mode_values(self) -> None:
        """Test that all cost modes have correct values."""
        assert CostMode.QUALITY.value == "QUALITY"
        assert CostMode.BALANCED.value == "BALANCED"
        assert CostMode.FAST.value == "FAST"
        assert CostMode.ECONOMY.value == "ECONOMY"

    def test_cost_mode_comparison(self) -> None:
        """Test cost mode comparison."""
        assert CostMode.QUALITY == CostMode.QUALITY
        assert CostMode.BALANCED != CostMode.FAST


class TestModeConfig:
    """Tests for ModeConfig dataclass."""

    def test_quality_config(self) -> None:
        """Test QUALITY mode configuration."""
        config = MODE_CONFIGS[CostMode.QUALITY]
        
        assert config.name == "Quality"
        assert config.screening_model == "gpt-5-mini"
        assert config.screening_dual_review is True
        assert config.extraction_model == "gpt-5-mini"
        assert config.extraction_triple_review is True
        assert config.use_full_text is True
        assert config.writing_model == "gpt-5.2-2025-12-11"
        assert config.max_reasoning_effort is True
        assert config.skip_rob is False
        assert config.skip_analysis is False
        assert config.minimal_writing is False

    def test_balanced_config(self) -> None:
        """Test BALANCED mode configuration."""
        config = MODE_CONFIGS[CostMode.BALANCED]
        
        assert config.name == "Balanced"
        assert config.screening_model == "gpt-5-nano"
        assert config.screening_dual_review is False
        assert config.extraction_model == "gpt-5-nano"
        assert config.extraction_triple_review is False
        assert config.use_full_text is True
        assert config.writing_model == "o3-mini"
        assert config.max_reasoning_effort is False
        assert config.skip_rob is False
        assert config.skip_analysis is False
        assert config.minimal_writing is False

    def test_fast_config(self) -> None:
        """Test FAST mode configuration."""
        config = MODE_CONFIGS[CostMode.FAST]
        
        assert config.name == "Fast"
        assert config.screening_model == "gpt-5-nano"
        assert config.screening_dual_review is False
        assert config.extraction_model == "gpt-5-nano"
        assert config.extraction_triple_review is False
        assert config.use_full_text is True
        assert config.writing_model == "o3-mini"
        assert config.skip_rob is True  # Key difference
        assert config.skip_analysis is True  # Key difference
        assert config.minimal_writing is False

    def test_economy_config(self) -> None:
        """Test ECONOMY mode configuration."""
        config = MODE_CONFIGS[CostMode.ECONOMY]
        
        assert config.name == "Economy"
        assert config.screening_model == "gpt-5-nano"
        assert config.screening_dual_review is False
        assert config.extraction_model == "gpt-5-nano"
        assert config.extraction_triple_review is False
        assert config.use_full_text is True
        assert config.writing_model == "o3-mini"
        assert config.skip_rob is True
        assert config.skip_analysis is True
        assert config.minimal_writing is True  # Key difference

    def test_all_modes_use_full_text(self) -> None:
        """Critical test: All modes MUST use full text."""
        for mode, config in MODE_CONFIGS.items():
            assert config.use_full_text is True, f"Mode {mode} must use full text"

    def test_quality_uses_dual_and_triple_review(self) -> None:
        """QUALITY mode should use dual/triple review."""
        config = MODE_CONFIGS[CostMode.QUALITY]
        assert config.screening_dual_review is True
        assert config.extraction_triple_review is True

    def test_non_quality_uses_single_review(self) -> None:
        """Non-quality modes should use single review."""
        for mode in [CostMode.BALANCED, CostMode.FAST, CostMode.ECONOMY]:
            config = MODE_CONFIGS[mode]
            assert config.screening_dual_review is False
            assert config.extraction_triple_review is False


class TestGetModeConfig:
    """Tests for get_mode_config function."""

    def test_get_config_by_enum(self) -> None:
        """Test getting config by enum."""
        config = get_mode_config(CostMode.QUALITY)
        assert config.name == "Quality"

    def test_get_config_by_string(self) -> None:
        """Test getting config by string."""
        config = get_mode_config("QUALITY")
        assert config.name == "Quality"
        
        config = get_mode_config("quality")  # Case insensitive
        assert config.name == "Quality"

    def test_get_config_invalid_mode(self) -> None:
        """Test getting config for invalid mode."""
        with pytest.raises(ValueError) as exc_info:
            get_mode_config("INVALID")
        
        assert "Invalid cost mode" in str(exc_info.value)


class TestGetDefaultMode:
    """Tests for default mode functions."""

    def test_default_mode_is_balanced(self) -> None:
        """Test that default mode is BALANCED."""
        assert get_default_mode() == CostMode.BALANCED

    def test_default_mode_config(self) -> None:
        """Test that default mode config is BALANCED."""
        config = get_default_mode_config()
        assert config.name == "Balanced"


class TestListModes:
    """Tests for list_modes function."""

    def test_list_modes_returns_all_modes(self) -> None:
        """Test that list_modes returns all 4 modes."""
        modes = list_modes()
        assert len(modes) == 4
        
        values = [m["value"] for m in modes]
        assert "QUALITY" in values
        assert "BALANCED" in values
        assert "FAST" in values
        assert "ECONOMY" in values

    def test_list_modes_has_required_fields(self) -> None:
        """Test that each mode has required fields."""
        modes = list_modes()
        
        for mode in modes:
            assert "value" in mode
            assert "name" in mode
            assert "description" in mode


class TestValidateMode:
    """Tests for validate_mode function."""

    def test_validate_valid_modes(self) -> None:
        """Test validating valid modes."""
        assert validate_mode("QUALITY") == CostMode.QUALITY
        assert validate_mode("balanced") == CostMode.BALANCED
        assert validate_mode("Fast") == CostMode.FAST
        assert validate_mode("economy") == CostMode.ECONOMY

    def test_validate_invalid_mode(self) -> None:
        """Test validating invalid mode."""
        with pytest.raises(ValueError) as exc_info:
            validate_mode("INVALID")
        
        assert "Invalid cost mode" in str(exc_info.value)
        assert "QUALITY" in str(exc_info.value)
        assert "BALANCED" in str(exc_info.value)


class TestModeConfigImmutability:
    """Tests that ModeConfig is immutable (frozen)."""

    def test_mode_config_is_frozen(self) -> None:
        """Test that ModeConfig cannot be modified."""
        config = MODE_CONFIGS[CostMode.BALANCED]
        
        with pytest.raises(AttributeError):
            config.name = "Modified"
