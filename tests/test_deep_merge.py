"""
Comprehensive unit tests for deep merge utility.

Tests cover all documented edge cases, configuration options, and error conditions
for the deep merge functionality including dictionaries, lists, Pydantic models,
and type mismatch handling.
"""

from pydantic import BaseModel
import pytest

from agentic_spec.utils.deep_merge import (
    DeepMergeError,
    ListStrategy,
    MergeConfig,
    NonePolicy,
    TypeMismatchPolicy,
    deep_merge,
    merge_configs,
    merge_lists,
    merge_models,
)


# Test Models for Pydantic integration testing
class SimpleModel(BaseModel):
    """Simple test model with basic fields."""

    name: str
    value: int = 0
    settings: dict = {}


class NestedModel(BaseModel):
    """Complex nested model for advanced testing."""

    id: str
    metadata: dict = {}
    tags: list[str] = []
    config: SimpleModel | None = None


class RequiredFieldModel(BaseModel):
    """Model with required and optional fields."""

    required_field: str
    optional_field: str | None = None
    default_field: int = 42


class TestBasicDictMerge:
    """Test basic dictionary merging functionality."""

    def test_simple_dict_merge(self):
        """Test merging two simple dictionaries."""
        target = {"a": 1, "b": 2}
        source = {"c": 3, "d": 4}
        result = deep_merge(target, source)

        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected
        # Verify immutability
        assert target == {"a": 1, "b": 2}
        assert source == {"c": 3, "d": 4}

    def test_nested_dict_merge(self):
        """Test merging nested dictionaries."""
        target = {"a": 1, "nested": {"b": 2, "c": 3}}
        source = {"nested": {"c": 99, "d": 4}, "e": 5}
        result = deep_merge(target, source)

        expected = {"a": 1, "nested": {"b": 2, "c": 99, "d": 4}, "e": 5}
        assert result == expected

    def test_deeply_nested_dict_merge(self):
        """Test merging deeply nested dictionaries."""
        target = {"level1": {"level2": {"level3": {"a": 1, "b": 2}}}}
        source = {
            "level1": {"level2": {"level3": {"b": 99, "c": 3}, "new_key": "value"}}
        }
        result = deep_merge(target, source)

        expected = {
            "level1": {
                "level2": {"level3": {"a": 1, "b": 99, "c": 3}, "new_key": "value"}
            }
        }
        assert result == expected

    def test_empty_dict_merge(self):
        """Test merging with empty dictionaries."""
        # Empty target
        result1 = deep_merge({}, {"a": 1, "b": 2})
        assert result1 == {"a": 1, "b": 2}

        # Empty source
        result2 = deep_merge({"a": 1, "b": 2}, {})
        assert result2 == {"a": 1, "b": 2}

        # Both empty
        result3 = deep_merge({}, {})
        assert result3 == {}


class TestListMerge:
    """Test list merging with different strategies."""

    def test_list_concat_default(self):
        """Test list concatenation (default strategy)."""
        target = [1, 2, 3]
        source = [4, 5, 6]
        result = deep_merge(target, source)

        expected = [1, 2, 3, 4, 5, 6]
        assert result == expected
        # Verify immutability
        assert target == [1, 2, 3]
        assert source == [4, 5, 6]

    def test_list_replace_strategy(self):
        """Test list replacement strategy."""
        config = MergeConfig(list_strategy=ListStrategy.REPLACE)
        target = [1, 2, 3]
        source = [4, 5, 6]
        result = deep_merge(target, source, config)

        expected = [4, 5, 6]
        assert result == expected

    def test_list_element_wise_strategy(self):
        """Test element-wise list merging."""
        config = MergeConfig(list_strategy=ListStrategy.ELEMENT_WISE)

        # Test with dictionaries in lists
        target = [{"a": 1}, {"b": 2}]
        source = [{"c": 3}, {"d": 4}, {"e": 5}]
        result = deep_merge(target, source, config)

        expected = [{"a": 1, "c": 3}, {"b": 2, "d": 4}, {"e": 5}]
        assert result == expected

    def test_list_element_wise_different_lengths(self):
        """Test element-wise merging with different list lengths."""
        config = MergeConfig(list_strategy=ListStrategy.ELEMENT_WISE)

        # Target longer than source
        target = [{"a": 1}, {"b": 2}, {"c": 3}]
        source = [{"x": 10}]
        result = deep_merge(target, source, config)

        expected = [{"a": 1, "x": 10}, {"b": 2}, {"c": 3}]
        assert result == expected

        # Source longer than target
        target = [{"a": 1}]
        source = [{"x": 10}, {"y": 20}, {"z": 30}]
        result = deep_merge(target, source, config)

        expected = [{"a": 1, "x": 10}, {"y": 20}, {"z": 30}]
        assert result == expected

    def test_empty_list_merge(self):
        """Test merging with empty lists."""
        # Empty target
        result1 = deep_merge([], [1, 2, 3])
        assert result1 == [1, 2, 3]

        # Empty source
        result2 = deep_merge([1, 2, 3], [])
        assert result2 == [1, 2, 3]

        # Both empty
        result3 = deep_merge([], [])
        assert result3 == []

    def test_nested_lists_in_dicts(self):
        """Test merging lists nested within dictionaries."""
        target = {"items": [1, 2], "config": {"tags": ["a", "b"]}}
        source = {"items": [3, 4], "config": {"tags": ["c", "d"]}}
        result = deep_merge(target, source)

        expected = {"items": [1, 2, 3, 4], "config": {"tags": ["a", "b", "c", "d"]}}
        assert result == expected


class TestPydanticModelMerge:
    """Test Pydantic model merging functionality."""

    def test_simple_model_merge(self):
        """Test merging simple Pydantic models."""
        model1 = SimpleModel(name="test1", value=10, settings={"a": 1})
        model2 = SimpleModel(name="test1", value=20, settings={"b": 2})

        result = deep_merge(model1, model2)

        assert isinstance(result, SimpleModel)
        assert result.name == "test1"
        assert result.value == 20  # Source overwrites
        assert result.settings == {"a": 1, "b": 2}  # Deep merge

    def test_nested_model_merge(self):
        """Test merging nested Pydantic models."""
        inner1 = SimpleModel(name="inner1", settings={"x": 1})
        inner2 = SimpleModel(name="inner1", settings={"y": 2})

        model1 = NestedModel(
            id="test", metadata={"version": 1}, tags=["tag1"], config=inner1
        )
        model2 = NestedModel(
            id="test", metadata={"author": "user"}, tags=["tag2"], config=inner2
        )

        result = deep_merge(model1, model2)

        assert isinstance(result, NestedModel)
        assert result.id == "test"
        assert result.metadata == {"version": 1, "author": "user"}
        assert result.tags == ["tag1", "tag2"]
        assert result.config.settings == {"x": 1, "y": 2}

    def test_model_with_none_fields(self):
        """Test merging models with None fields."""
        model1 = RequiredFieldModel(required_field="test", optional_field=None)
        model2 = RequiredFieldModel(required_field="test", optional_field="value")

        result = deep_merge(model1, model2)

        assert result.required_field == "test"
        assert result.optional_field == "value"
        assert result.default_field == 42

    def test_model_validation_after_merge(self):
        """Test that merged models maintain validation."""
        model1 = SimpleModel(name="test", value=10)
        model2 = SimpleModel(name="test", value=20)

        result = deep_merge(model1, model2)

        # Result should still be valid
        assert isinstance(result, SimpleModel)
        assert result.model_validate(result.model_dump()) == result

    def test_different_model_types_error(self):
        """Test error when merging different model types."""
        model1 = SimpleModel(name="test")
        model2 = RequiredFieldModel(required_field="test")

        with pytest.raises(DeepMergeError) as exc_info:
            deep_merge(model1, model2)

        assert "Type mismatch" in str(exc_info.value)
        assert "SimpleModel" in str(exc_info.value)
        assert "RequiredFieldModel" in str(exc_info.value)


class TestNoneHandling:
    """Test None value handling with different policies."""

    def test_none_policy_skip_none(self):
        """Test SKIP_NONE policy (default)."""
        config = MergeConfig(none_policy=NonePolicy.SKIP_NONE)

        # None source should return target
        result1 = deep_merge({"a": 1}, None, config)
        assert result1 == {"a": 1}

        # None target should return source
        result2 = deep_merge(None, {"a": 1}, config)
        assert result2 == {"a": 1}

        # Both None should return None
        result3 = deep_merge(None, None, config)
        assert result3 is None

    def test_none_policy_allow_none(self):
        """Test ALLOW_NONE policy."""
        config = MergeConfig(none_policy=NonePolicy.ALLOW_NONE)

        # None source should override target
        result1 = deep_merge({"a": 1}, None, config)
        assert result1 is None

        # None target should return source
        result2 = deep_merge(None, {"a": 1}, config)
        assert result2 == {"a": 1}

    def test_none_values_in_nested_structures(self):
        """Test None values within nested structures."""
        target = {"a": 1, "nested": {"b": 2, "c": None}}
        source = {"nested": {"c": 3, "d": None}}

        result = deep_merge(target, source)

        # With SKIP_NONE (default), None values don't override
        expected = {"a": 1, "nested": {"b": 2, "c": 3, "d": None}}
        assert result == expected


class TestTypeMismatchHandling:
    """Test type mismatch handling with different policies."""

    def test_type_mismatch_error_policy(self):
        """Test ERROR policy for type mismatches (default)."""
        target = {"a": {"nested": "dict"}}
        source = {"a": [1, 2, 3]}  # Different type

        with pytest.raises(DeepMergeError) as exc_info:
            deep_merge(target, source)

        error = exc_info.value
        assert "Type mismatch" in str(error)
        assert "list" in str(error) and "dict" in str(error)
        assert error.path == ["a"]

    def test_type_mismatch_skip_policy(self):
        """Test SKIP policy for type mismatches."""
        config = MergeConfig(type_mismatch_policy=TypeMismatchPolicy.SKIP)

        target = {"a": {"nested": "dict"}, "b": 2}
        source = {"a": [1, 2, 3], "b": 3}  # 'a' is type mismatch, 'b' is same type

        result = deep_merge(target, source, config)

        # 'a' should be skipped (keep target), 'b' should be merged
        expected = {"a": {"nested": "dict"}, "b": 3}
        assert result == expected

    def test_type_mismatch_force_policy(self):
        """Test FORCE policy for type mismatches."""
        config = MergeConfig(type_mismatch_policy=TypeMismatchPolicy.FORCE)

        target = {"a": {"nested": "dict"}, "b": 2}
        source = {"a": [1, 2, 3], "b": 3}

        result = deep_merge(target, source, config)

        # 'a' should be forced to source value, 'b' should be merged normally
        expected = {"a": [1, 2, 3], "b": 3}
        assert result == expected

    def test_primitive_type_mismatches(self):
        """Test type mismatches with primitive types."""
        config = MergeConfig(type_mismatch_policy=TypeMismatchPolicy.SKIP)

        target = {"str_field": "text", "int_field": 42, "bool_field": True}
        source = {"str_field": 123, "int_field": "not_int", "bool_field": "not_bool"}

        result = deep_merge(target, source, config)

        # All should be skipped due to type mismatches
        assert result == target


class TestErrorHandling:
    """Test error conditions and edge cases."""

    def test_recursion_depth_limit(self):
        """Test maximum recursion depth protection."""
        config = MergeConfig(max_depth=3)

        # Create deeply nested structure exceeding limit
        deep_target = {"l1": {"l2": {"l3": {"l4": {"l5": "too_deep"}}}}}
        deep_source = {"l1": {"l2": {"l3": {"l4": {"l6": "also_deep"}}}}}

        with pytest.raises(DeepMergeError) as exc_info:
            deep_merge(deep_target, deep_source, config)

        assert "Maximum merge depth" in str(exc_info.value)
        assert "circular reference" in str(exc_info.value)

    def test_invalid_list_strategy(self):
        """Test error on invalid list strategy."""
        # This would be caught by Pydantic validation, but let's test the enum
        with pytest.raises(ValueError):
            MergeConfig(list_strategy="invalid_strategy")

    def test_invalid_type_mismatch_policy(self):
        """Test error on invalid type mismatch policy."""
        with pytest.raises(ValueError):
            MergeConfig(type_mismatch_policy="invalid_policy")

    def test_model_validation_error(self):
        """Test handling of model validation errors during merge."""
        # Test that DeepMergeError has the expected attributes
        error = DeepMergeError(
            "test message", path=["test"], source_type=str, target_type=int
        )

        assert hasattr(error, "path")
        assert hasattr(error, "source_type")
        assert hasattr(error, "target_type")
        assert error.path == ["test"]
        assert error.source_type == str
        assert error.target_type == int

    def test_error_path_tracking(self):
        """Test that error paths are correctly tracked."""
        target = {"level1": {"level2": {"problem": {"nested": "dict"}}}}
        source = {"level1": {"level2": {"problem": [1, 2, 3]}}}

        with pytest.raises(DeepMergeError) as exc_info:
            deep_merge(target, source)

        error = exc_info.value
        assert error.path == ["level1", "level2", "problem"]
        assert "level1 -> level2 -> problem" in str(error)


class TestConvenienceFunctions:
    """Test convenience functions for common use cases."""

    def test_merge_configs_function(self):
        """Test merge_configs convenience function."""
        base = {
            "database": {"host": "localhost", "port": 5432},
            "features": ["auth", "logging"],
        }
        override = {
            "database": {"port": 3306, "ssl": True},
            "features": ["monitoring"],
            "debug": True,
        }

        result = merge_configs(base, override)

        expected = {
            "database": {"host": "localhost", "port": 3306, "ssl": True},
            "features": ["auth", "logging", "monitoring"],
            "debug": True,
        }
        assert result == expected

    def test_merge_models_function(self):
        """Test merge_models convenience function."""
        model1 = SimpleModel(name="test", value=10, settings={"a": 1})
        model2 = SimpleModel(name="test", value=20, settings={"b": 2})

        result = merge_models(model1, model2)

        assert isinstance(result, SimpleModel)
        assert result.name == "test"
        assert result.value == 20
        assert result.settings == {"a": 1, "b": 2}

    def test_merge_models_strict_types(self):
        """Test merge_models with strict type checking."""
        model1 = SimpleModel(name="test")
        model2 = RequiredFieldModel(required_field="test")

        # Strict mode should raise error
        with pytest.raises(DeepMergeError):
            merge_models(model1, model2, strict_types=True)

        # Non-strict mode should skip mismatched models
        result = merge_models(model1, model2, strict_types=False)
        assert result == model1  # Should keep target unchanged

    def test_merge_lists_function(self):
        """Test merge_lists convenience function."""
        list1 = [1, 2, 3]
        list2 = [4, 5, 6]

        # Default concatenation
        result1 = merge_lists(list1, list2)
        assert result1 == [1, 2, 3, 4, 5, 6]

        # Replacement strategy
        result2 = merge_lists(list1, list2, ListStrategy.REPLACE)
        assert result2 == [4, 5, 6]


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_configuration_inheritance_scenario(self):
        """Test scenario similar to agentic-spec configuration inheritance."""
        base_config = {
            "ai_provider": "openai",
            "model_settings": {"temperature": 0.7, "max_tokens": 1000, "top_p": 1.0},
            "templates": ["base"],
            "workflow": {"strict_mode": True, "auto_approve": False},
        }

        user_config = {
            "model_settings": {
                "temperature": 0.5,  # Override
                "presence_penalty": 0.1,  # New setting
            },
            "templates": ["web-api", "cli-app"],  # Additional templates
            "workflow": {
                "auto_approve": True  # Override
            },
            "debug": True,  # New setting
        }

        result = merge_configs(base_config, user_config)

        expected = {
            "ai_provider": "openai",
            "model_settings": {
                "temperature": 0.5,
                "max_tokens": 1000,
                "top_p": 1.0,
                "presence_penalty": 0.1,
            },
            "templates": ["base", "web-api", "cli-app"],
            "workflow": {"strict_mode": True, "auto_approve": True},
            "debug": True,
        }
        assert result == expected

    def test_specification_template_inheritance(self):
        """Test scenario for specification template inheritance."""
        base_template = {
            "version": "1.0",
            "coding_standards": {
                "style": "pep8",
                "docstrings": True,
                "type_hints": True,
            },
            "testing": {"framework": "pytest", "coverage": 90},
            "requirements": ["high_quality", "maintainable"],
        }

        web_api_template = {
            "version": "1.1",  # Override
            "coding_standards": {
                "async_patterns": True,  # Add new standard
                "error_handling": "structured",  # Add new standard
            },
            "testing": {
                "api_tests": True  # Add API-specific testing
            },
            "requirements": ["scalable", "secure"],  # Additional requirements
            "dependencies": ["fastapi", "pydantic"],  # New section
        }

        result = deep_merge(base_template, web_api_template)

        expected = {
            "version": "1.1",
            "coding_standards": {
                "style": "pep8",
                "docstrings": True,
                "type_hints": True,
                "async_patterns": True,
                "error_handling": "structured",
            },
            "testing": {"framework": "pytest", "coverage": 90, "api_tests": True},
            "requirements": ["high_quality", "maintainable", "scalable", "secure"],
            "dependencies": ["fastapi", "pydantic"],
        }
        assert result == expected

    def test_mixed_data_types_scenario(self):
        """Test scenario with mixed data types and complex nesting."""
        target = {
            "metadata": {
                "version": 1,
                "tags": ["v1", "stable"],
                "config": SimpleModel(name="base", value=100),
            },
            "features": {
                "auth": {"enabled": True, "providers": ["oauth"]},
                "logging": {"level": "info", "handlers": [{"type": "file"}]},
            },
        }

        source = {
            "metadata": {
                "version": 2,  # Override
                "tags": ["v2", "beta"],  # Concatenate
                "config": SimpleModel(
                    name="base", value=200, settings={"new": True}
                ),  # Merge models
            },
            "features": {
                "auth": {"providers": ["saml"]},  # Merge nested dict, concatenate list
                "monitoring": {"enabled": True},  # New feature
            },
        }

        result = deep_merge(target, source)

        # Verify structure
        assert result["metadata"]["version"] == 2
        assert result["metadata"]["tags"] == ["v1", "stable", "v2", "beta"]
        assert isinstance(result["metadata"]["config"], SimpleModel)
        assert result["metadata"]["config"].value == 200
        assert result["metadata"]["config"].settings == {"new": True}

        assert result["features"]["auth"]["enabled"] is True
        assert result["features"]["auth"]["providers"] == ["oauth", "saml"]
        assert result["features"]["monitoring"]["enabled"] is True


class TestImmutability:
    """Test that deep merge operations are truly immutable."""

    def test_input_immutability_dicts(self):
        """Test that input dictionaries are not modified."""
        target = {"a": 1, "nested": {"b": 2}}
        source = {"nested": {"c": 3}, "d": 4}

        target_copy = {"a": 1, "nested": {"b": 2}}
        source_copy = {"nested": {"c": 3}, "d": 4}

        result = deep_merge(target, source)

        # Inputs should be unchanged
        assert target == target_copy
        assert source == source_copy

        # Result should be different object
        assert result is not target
        assert result["nested"] is not target["nested"]

    def test_input_immutability_lists(self):
        """Test that input lists are not modified."""
        target = [1, 2, {"nested": "dict"}]
        source = [3, 4, {"other": "value"}]

        target_copy = [1, 2, {"nested": "dict"}]
        source_copy = [3, 4, {"other": "value"}]

        result = deep_merge(target, source)

        # Inputs should be unchanged
        assert target == target_copy
        assert source == source_copy

        # Result should be different object
        assert result is not target

    def test_input_immutability_models(self):
        """Test that input models are not modified."""
        model1 = SimpleModel(name="test", value=10, settings={"a": 1})
        model2 = SimpleModel(name="test", value=20, settings={"b": 2})

        original_settings1 = model1.settings.copy()
        original_settings2 = model2.settings.copy()

        result = deep_merge(model1, model2)

        # Original models should be unchanged
        assert model1.settings == original_settings1
        assert model2.settings == original_settings2

        # Result should be different instance
        assert result is not model1
        assert result is not model2


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
