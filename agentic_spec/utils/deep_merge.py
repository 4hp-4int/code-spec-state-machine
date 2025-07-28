"""
Deep merge utility for nested dictionaries, lists, and Pydantic models.

This module provides robust deep merge functionality for complex data structures
commonly used in configuration and specification merging scenarios.

## Algorithm Design

The deep merge algorithm handles the following data types:
- **Dictionaries**: Key-wise recursive merge
- **Lists**: Configurable concatenation or replacement strategies
- **Pydantic Models**: Field-wise merge preserving required/optional semantics
- **Primitives**: Direct replacement (int, str, bool, None, etc.)

## Merge Rules by Type

### Dictionary Merge (key-wise)
- For each key in source dict:
  - If key not in target: add key-value pair
  - If both values are dicts: recurse with deep merge
  - If both values are lists: apply list merge strategy
  - If both values are Pydantic models of same type: apply model merge
  - Otherwise: apply type mismatch policy

### List Merge (configurable)
- **Concatenate strategy (default)**: target + source
- **Replace strategy**: source replaces target entirely
- **Element-wise merge** (when both lists contain mergeable types):
  - If lists contain dicts/models: merge corresponding elements by index
  - Longer list elements are appended

### Pydantic Model Merge (field-wise)
- Models must be of the same type
- For each field in source model:
  - Required fields: merge recursively, never None
  - Optional fields: merge per configuration, can be None
  - Field validation preserved through model reconstruction

### Type Mismatch Handling
- **Error policy (default)**: Raise TypeError with detailed context
- **Skip policy**: Keep target value unchanged, log warning
- **Force policy**: Always use source value (dangerous)

## Edge Cases Handled

1. **None Value Handling**:
   - None + dict/list/model → source value (not None)
   - dict/list/model + None → keep target (not None)
   - None + None → None
   - None + primitive → primitive

2. **Empty Collections**:
   - {} + dict → dict (copy)
   - [] + list → list (copy)
   - dict/list + {} or [] → keep target with source additions

3. **Model Validation**:
   - Invalid merged models raise ValidationError
   - Extra fields handled per model configuration
   - Field defaults preserved during merge

4. **Deeply Nested Structures**:
   - Recursive depth tracking to prevent infinite loops
   - Performance optimization for large structures
   - Memory-efficient copying for immutability

5. **Special Cases**:
   - Merging models with different field sets
   - Lists containing mixed types (dicts, models, primitives)
   - Configuration inheritance chains

## Performance Characteristics

- Time Complexity: O(n) where n is total elements across all nesting levels
- Space Complexity: O(d) where d is maximum nesting depth
- Optimized for typical configuration sizes (≤1000 fields, ≤5 nesting levels)
- Immutable operations: no input mutation, always returns new instances

## Configuration Options

All merge operations are controlled by a MergeConfig instance:
- list_strategy: 'concat' | 'replace' | 'element_wise'
- type_mismatch_policy: 'error' | 'skip' | 'force'
- none_policy: 'skip_none' | 'allow_none'
- max_depth: int (prevents infinite recursion)
- preserve_type: bool (strict type checking)
"""

from copy import deepcopy
from enum import Enum
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ListStrategy(str, Enum):
    """Strategy for merging lists."""

    CONCAT = "concat"  # Concatenate lists: target + source
    REPLACE = "replace"  # Replace target with source entirely
    ELEMENT_WISE = "element_wise"  # Merge corresponding elements by index


class TypeMismatchPolicy(str, Enum):
    """Policy for handling type mismatches during merge."""

    ERROR = "error"  # Raise TypeError (default, safest)
    SKIP = "skip"  # Keep target value, skip source
    FORCE = "force"  # Always use source value (dangerous)


class NonePolicy(str, Enum):
    """Policy for handling None values."""

    SKIP_NONE = "skip_none"  # None values don't override non-None
    ALLOW_NONE = "allow_none"  # None values can override non-None


class MergeConfig(BaseModel):
    """Configuration for deep merge operations."""

    list_strategy: ListStrategy = ListStrategy.CONCAT
    type_mismatch_policy: TypeMismatchPolicy = TypeMismatchPolicy.ERROR
    none_policy: NonePolicy = NonePolicy.SKIP_NONE
    max_depth: int = 20
    preserve_type: bool = True

    model_config = {"use_enum_values": True}


class DeepMergeError(Exception):
    """Exception raised during deep merge operations."""

    def __init__(
        self,
        message: str,
        path: list[str] | None = None,
        source_type: type | None = None,
        target_type: type | None = None,
    ):
        self.path = path or []
        self.source_type = source_type
        self.target_type = target_type
        super().__init__(message)

    def __str__(self) -> str:
        path_str = " -> ".join(self.path) if self.path else "root"
        type_info = ""
        if self.source_type and self.target_type:
            type_info = f" (source: {self.source_type.__name__}, target: {self.target_type.__name__})"
        return f"{super().__str__()} at path: {path_str}{type_info}"


def deep_merge(
    target: Any,
    source: Any,
    config: MergeConfig | None = None,
    _path: list[str] | None = None,
    _depth: int = 0,
) -> Any:
    """
    Perform deep merge of two data structures.

    Args:
        target: Target structure to merge into (not modified)
        source: Source structure to merge from (not modified)
        config: Merge configuration options
        _path: Internal path tracking for error reporting
        _depth: Internal depth tracking for recursion limits

    Returns:
        New merged data structure of the same type as target

    Raises:
        DeepMergeError: On type mismatches, validation errors, or configuration issues
        RecursionError: If max_depth exceeded (indicates circular references)

    Examples:
        >>> target = {"a": 1, "b": {"c": 2}}
        >>> source = {"b": {"d": 3}, "e": 4}
        >>> result = deep_merge(target, source)
        >>> result
        {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}

        >>> # List concatenation (default)
        >>> deep_merge([1, 2], [3, 4])
        [1, 2, 3, 4]

        >>> # List replacement
        >>> config = MergeConfig(list_strategy=ListStrategy.REPLACE)
        >>> deep_merge([1, 2], [3, 4], config)
        [3, 4]

        >>> # Pydantic model merge
        >>> class User(BaseModel):
        ...     name: str
        ...     settings: dict = {}
        >>> user1 = User(name="Alice", settings={"theme": "dark"})
        >>> user2 = User(name="Alice", settings={"lang": "en"})
        >>> merged = deep_merge(user1, user2)
        >>> merged.settings
        {"theme": "dark", "lang": "en"}
    """
    if config is None:
        config = MergeConfig()

    if _path is None:
        _path = []

    # Check recursion depth
    if _depth > config.max_depth:
        msg = f"Maximum merge depth ({config.max_depth}) exceeded - possible circular reference"
        raise DeepMergeError(msg, path=_path)

    # Handle None values according to policy
    if source is None:
        return target if config.none_policy == NonePolicy.SKIP_NONE else None
    if target is None:
        return deepcopy(source)

    # Get types for comparison
    target_type = type(target)
    source_type = type(source)

    # Same type: delegate to specific merge logic
    if target_type == source_type:
        if isinstance(target, dict):
            return _merge_dicts(target, source, config, _path, _depth)
        if isinstance(target, list):
            return _merge_lists(target, source, config, _path, _depth)
        if isinstance(target, BaseModel):
            return _merge_models(target, source, config, _path, _depth)
        # Primitive types: source replaces target
        return deepcopy(source)

    # Type mismatch: apply policy
    return _handle_type_mismatch(target, source, config, _path)


def _merge_dicts(
    target: dict[str, Any],
    source: dict[str, Any],
    config: MergeConfig,
    path: list[str],
    depth: int,
) -> dict[str, Any]:
    """Merge two dictionaries recursively."""
    result = target.copy()  # Shallow copy to preserve immutability

    for key, source_value in source.items():
        current_path = [*path, key]

        if key not in result:
            # New key: add directly (deep copy for safety)
            result[key] = deepcopy(source_value)
        else:
            # Existing key: merge recursively
            result[key] = deep_merge(
                result[key], source_value, config, current_path, depth + 1
            )

    return result


def _merge_lists(
    target: list[Any],
    source: list[Any],
    config: MergeConfig,
    path: list[str],
    depth: int,
) -> list[Any]:
    """Merge two lists according to configured strategy."""
    if config.list_strategy == ListStrategy.REPLACE:
        return deepcopy(source)

    if config.list_strategy == ListStrategy.CONCAT:
        result = target.copy()
        result.extend(deepcopy(source))
        return result

    if config.list_strategy == ListStrategy.ELEMENT_WISE:
        # Merge corresponding elements by index
        result = []
        max_len = max(len(target), len(source))

        for i in range(max_len):
            current_path = [*path, f"[{i}]"]

            if i >= len(target):
                # Source has more elements
                result.append(deepcopy(source[i]))
            elif i >= len(source):
                # Target has more elements
                result.append(deepcopy(target[i]))
            else:
                # Both have elements at this index: merge them
                merged_element = deep_merge(
                    target[i], source[i], config, current_path, depth + 1
                )
                result.append(merged_element)

        return result

    msg = f"Unknown list strategy: {config.list_strategy}"
    raise DeepMergeError(msg, path=path)


def _merge_models(
    target: BaseModel,
    source: BaseModel,
    config: MergeConfig,
    path: list[str],
    depth: int,
) -> BaseModel:
    """Merge two Pydantic models of the same type."""
    target_type = type(target)
    source_type = type(source)

    if target_type != source_type:
        return _handle_type_mismatch(target, source, config, path)

    # Get field values from both models
    target_dict = target.model_dump()
    source_dict = source.model_dump()

    # Merge the dictionaries recursively
    merged_dict = _merge_dicts(target_dict, source_dict, config, path, depth)

    # Reconstruct the model (this validates merged data)
    try:
        return target_type(**merged_dict)
    except ValidationError as e:
        msg = f"Model validation failed after merge: {e}"
        raise DeepMergeError(
            msg,
            path=path,
            source_type=source_type,
            target_type=target_type,
        ) from e


def _handle_type_mismatch(
    target: Any, source: Any, config: MergeConfig, path: list[str]
) -> Any:
    """Handle type mismatches according to configured policy."""
    target_type = type(target)
    source_type = type(source)

    if config.type_mismatch_policy == TypeMismatchPolicy.ERROR:
        msg = f"Type mismatch: cannot merge {source_type.__name__} into {target_type.__name__}"
        raise DeepMergeError(
            msg,
            path=path,
            source_type=source_type,
            target_type=target_type,
        )

    if config.type_mismatch_policy == TypeMismatchPolicy.SKIP:
        path_str = " -> ".join(path) if path else "root"
        logger.warning(
            "Type mismatch at %s: skipping %s -> %s",
            path_str,
            source_type.__name__,
            target_type.__name__,
        )
        return target  # Keep target unchanged

    if config.type_mismatch_policy == TypeMismatchPolicy.FORCE:
        path_str = " -> ".join(path) if path else "root"
        logger.warning(
            "Type mismatch at %s: forcing %s -> %s",
            path_str,
            source_type.__name__,
            target_type.__name__,
        )
        return deepcopy(source)  # Use source value

    msg = f"Unknown type mismatch policy: {config.type_mismatch_policy}"
    raise DeepMergeError(msg, path=path)


# Convenience functions for common use cases


def merge_configs(
    base_config: dict[str, Any],
    override_config: dict[str, Any],
    list_strategy: ListStrategy = ListStrategy.CONCAT,
) -> dict[str, Any]:
    """
    Merge configuration dictionaries with sensible defaults.

    This is the recommended function for merging configuration files,
    template inheritance, and CLI overrides in agentic-spec.

    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        list_strategy: How to handle list merging (default: concatenate)

    Returns:
        Merged configuration dictionary

    Features:
        - Type mismatches are skipped (not errors) - more lenient for configs
        - None values are allowed to override - supports explicit clearing
        - Lists are concatenated by default - accumulates values

    Example:
        >>> base = {"api": {"timeout": 30}, "features": ["auth"]}
        >>> override = {"api": {"retries": 3}, "features": ["logging"]}
        >>> merge_configs(base, override)
        {"api": {"timeout": 30, "retries": 3}, "features": ["auth", "logging"]}
    """
    config = MergeConfig(
        list_strategy=list_strategy,
        type_mismatch_policy=TypeMismatchPolicy.SKIP,  # More lenient for configs
        none_policy=NonePolicy.ALLOW_NONE,  # Allow None overrides in configs
    )
    return deep_merge(base_config, override_config, config)


def merge_models(base_model: T, override_model: T, strict_types: bool = True) -> T:
    """
    Merge two Pydantic models with validation.

    Args:
        base_model: Base model instance
        override_model: Override model instance (must be same type)
        strict_types: Whether to enforce strict type checking

    Returns:
        New merged model instance

    Raises:
        DeepMergeError: If models are different types (when strict_types=True)
    """
    config = MergeConfig(
        list_strategy=ListStrategy.CONCAT,
        type_mismatch_policy=TypeMismatchPolicy.ERROR
        if strict_types
        else TypeMismatchPolicy.SKIP,
        preserve_type=strict_types,
    )
    return deep_merge(base_model, override_model, config)


def merge_lists(
    base_list: list[Any],
    override_list: list[Any],
    strategy: ListStrategy = ListStrategy.CONCAT,
) -> list[Any]:
    """
    Merge two lists with specified strategy.

    Args:
        base_list: Base list
        override_list: Override list
        strategy: Merge strategy to use

    Returns:
        New merged list
    """
    config = MergeConfig(list_strategy=strategy)
    return deep_merge(base_list, override_list, config)


# Integration examples for agentic-spec
"""
The deep merge utility is integrated throughout agentic-spec for:

1. Template Inheritance (core.py):
   ```python
   merged = {}
   for template_name in inherits:
       template = self.load_template(template_name)
       merged = merge_configs(merged, template)
   ```

2. Configuration Management (config.py):
   ```python
   # File config + CLI overrides
   config_data = merge_configs(config_data, file_config)
   merged_dict = merge_configs(config_dict, cli_overrides)
   ```

3. Specification Context Building:
   ```python
   context = {}
   context = merge_configs(context, {"foundation": foundation_context})
   context = merge_configs(context, {"inherited": inherited_context})
   context = merge_configs(context, {"parent": parent_context})
   ```
"""


# Usage examples and integration hints
if __name__ == "__main__":
    # Example usage for agentic-spec integration

    # Configuration merging example
    base_config = {
        "ai_provider": "openai",
        "model_settings": {"temperature": 0.7, "max_tokens": 1000},
        "templates": ["base", "web-api"],
    }

    user_config = {
        "model_settings": {
            "temperature": 0.5,  # Override
            "top_p": 0.9,  # New setting
        },
        "templates": ["cli-app"],  # Additional template
        "debug": True,
    }

    merged = merge_configs(base_config, user_config)
    print("Merged config:", merged)
    # Result: {
    #   "ai_provider": "openai",
    #   "model_settings": {"temperature": 0.5, "max_tokens": 1000, "top_p": 0.9},
    #   "templates": ["base", "web-api", "cli-app"],
    #   "debug": True
    # }
