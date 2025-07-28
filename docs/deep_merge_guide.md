# Deep Merge Utility Guide

## Overview

The deep merge utility provides robust, configurable merging of complex Python data structures including dictionaries, lists, and Pydantic models. It was designed to handle the sophisticated template inheritance and configuration merging requirements of the agentic-spec tool.

## Key Features

- **Immutable operations**: Never modifies input data structures
- **Type-safe**: Handles type mismatches with configurable policies
- **Pydantic-aware**: Seamlessly merges Pydantic models with validation
- **Highly configurable**: Control merge behavior for different use cases
- **Production-ready**: Comprehensive error handling and edge case coverage

## Quick Start

### Basic Dictionary Merge

```python
from agentic_spec.utils.deep_merge import deep_merge

target = {"a": 1, "b": {"c": 2}}
source = {"b": {"d": 3}, "e": 4}
result = deep_merge(target, source)
# Result: {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}
```

### Configuration Merge (Common Use Case)

```python
from agentic_spec.utils.deep_merge import merge_configs

base_config = {
    "ai_provider": "openai",
    "model_settings": {"temperature": 0.7, "max_tokens": 1000},
    "templates": ["base"]
}

user_config = {
    "model_settings": {"temperature": 0.5, "top_p": 0.9},
    "templates": ["web-api"],
    "debug": True
}

merged = merge_configs(base_config, user_config)
# Result: {
#   "ai_provider": "openai",
#   "model_settings": {"temperature": 0.5, "max_tokens": 1000, "top_p": 0.9},
#   "templates": ["base", "web-api"],
#   "debug": True
# }
```

## Configuration Options

### MergeConfig Parameters

```python
from agentic_spec.utils.deep_merge import MergeConfig, ListStrategy, TypeMismatchPolicy, NonePolicy

config = MergeConfig(
    list_strategy=ListStrategy.CONCAT,           # How to merge lists
    type_mismatch_policy=TypeMismatchPolicy.ERROR,  # How to handle type conflicts
    none_policy=NonePolicy.SKIP_NONE,           # How to handle None values
    max_depth=20,                               # Maximum recursion depth
    preserve_type=True                          # Strict type checking
)
```

### List Merge Strategies

1. **CONCAT** (default): Concatenate lists
   ```python
   deep_merge([1, 2], [3, 4])  # → [1, 2, 3, 4]
   ```

2. **REPLACE**: Replace target list with source
   ```python
   config = MergeConfig(list_strategy=ListStrategy.REPLACE)
   deep_merge([1, 2], [3, 4], config)  # → [3, 4]
   ```

3. **ELEMENT_WISE**: Merge corresponding elements by index
   ```python
   config = MergeConfig(list_strategy=ListStrategy.ELEMENT_WISE)
   deep_merge([{"a": 1}, {"b": 2}], [{"c": 3}], config)
   # → [{"a": 1, "c": 3}, {"b": 2}]
   ```

### Type Mismatch Policies

1. **ERROR** (default): Raise exception on type mismatch
   ```python
   deep_merge({"a": {}}, {"a": []})  # Raises DeepMergeError
   ```

2. **SKIP**: Keep target value on type mismatch
   ```python
   config = MergeConfig(type_mismatch_policy=TypeMismatchPolicy.SKIP)
   deep_merge({"a": {}, "b": 1}, {"a": [], "b": 2}, config)
   # → {"a": {}, "b": 2}  # 'a' skipped, 'b' merged
   ```

3. **FORCE**: Always use source value
   ```python
   config = MergeConfig(type_mismatch_policy=TypeMismatchPolicy.FORCE)
   deep_merge({"a": {}}, {"a": []}, config)  # → {"a": []}
   ```

### None Value Policies

1. **SKIP_NONE** (default): None values don't override non-None
   ```python
   deep_merge({"a": 1}, {"a": None})  # → {"a": 1}
   ```

2. **ALLOW_NONE**: None values can override
   ```python
   config = MergeConfig(none_policy=NonePolicy.ALLOW_NONE)
   deep_merge({"a": 1}, {"a": None}, config)  # → {"a": None}
   ```

## Advanced Usage

### Pydantic Model Merging

```python
from pydantic import BaseModel
from agentic_spec.utils.deep_merge import merge_models

class UserSettings(BaseModel):
    theme: str = "light"
    notifications: dict = {}

user1 = UserSettings(theme="dark", notifications={"email": True})
user2 = UserSettings(theme="dark", notifications={"sms": True})

merged = merge_models(user1, user2)
# merged.notifications = {"email": True, "sms": True}
```

### Template Inheritance Pattern

This pattern is used extensively in agentic-spec for template composition:

```python
def inherit_templates(template_names: list[str]) -> dict:
    """Merge multiple templates in order."""
    result = {}
    for name in template_names:
        template = load_template(name)
        result = merge_configs(result, template)
    return result

# Usage
final_config = inherit_templates(["base", "web-api", "security-enhanced"])
```

### Custom Merge for Specific Fields

```python
def merge_with_custom_rules(base: dict, override: dict) -> dict:
    """Merge with different strategies for different fields."""
    # Replace lists for 'tags', concatenate for everything else
    result = base.copy()

    for key, value in override.items():
        if key == "tags":
            config = MergeConfig(list_strategy=ListStrategy.REPLACE)
        else:
            config = MergeConfig(list_strategy=ListStrategy.CONCAT)

        if key in result:
            result[key] = deep_merge(result[key], value, config)
        else:
            result[key] = value

    return result
```

## Edge Cases and Behaviors

### Empty Collections

- Empty dictionaries/lists as target: Source is copied
- Empty dictionaries/lists as source: Target is preserved
- Both empty: Empty result

```python
deep_merge({}, {"a": 1})  # → {"a": 1}
deep_merge({"a": 1}, {})  # → {"a": 1}
deep_merge([], [1, 2])    # → [1, 2]
```

### Circular References

The utility protects against infinite recursion:

```python
config = MergeConfig(max_depth=3)
deeply_nested = {"a": {"b": {"c": {"d": "too deep"}}}}
# Will raise DeepMergeError if depth exceeded
```

### Mixed Type Lists

Element-wise merging handles mixed types gracefully:

```python
config = MergeConfig(list_strategy=ListStrategy.ELEMENT_WISE)
target = [{"dict": 1}, "string", 123]
source = [{"other": 2}, "other_string"]
result = deep_merge(target, source, config)
# → [{"dict": 1, "other": 2}, "other_string", 123]
```

### Model Validation

Merged Pydantic models are always validated:

```python
class StrictModel(BaseModel):
    value: int  # Must be integer

model1 = StrictModel(value=10)
# This would fail validation after merge:
# invalid_dict = {"value": "not_an_integer"}
```

## Error Handling

### DeepMergeError

All merge errors raise `DeepMergeError` with detailed context:

```python
try:
    deep_merge({"a": {"b": {}}}, {"a": {"b": []}})
except DeepMergeError as e:
    print(e)  # "Type mismatch: cannot merge list into dict at path: a -> b"
    print(e.path)  # ["a", "b"]
    print(e.source_type)  # <class 'list'>
    print(e.target_type)  # <class 'dict'>
```

### Path Tracking

Errors include the full path to the conflict:

```python
data = {
    "config": {
        "database": {
            "connections": {
                "primary": {"host": "localhost"}
            }
        }
    }
}

# Error would show path: config -> database -> connections -> primary
```

## Performance Considerations

1. **Immutability**: All operations create new objects. For very large structures, consider the memory impact.

2. **Recursion Depth**: Default max_depth=20 prevents stack overflow. Adjust for deeper structures:
   ```python
   config = MergeConfig(max_depth=50)
   ```

3. **List Concatenation**: For large lists, CONCAT strategy is O(n+m). Consider REPLACE for better performance.

## Best Practices

1. **Use Convenience Functions**: For common cases, use `merge_configs()`, `merge_models()`, etc.

2. **Choose Appropriate Strategies**:
   - Configuration files: Use `merge_configs()` (lenient)
   - API responses: Use strict type checking
   - User preferences: Allow None overrides

3. **Handle Errors Gracefully**:
   ```python
   try:
       result = deep_merge(target, source)
   except DeepMergeError as e:
       logger.error(f"Merge failed at {' -> '.join(e.path)}")
       # Fallback logic
   ```

4. **Test Edge Cases**: Always test with empty collections, None values, and type mismatches.

## Integration with agentic-spec

The deep merge utility is integrated into:

1. **Template Inheritance**: `core.py` uses it for multi-template composition
2. **Configuration Loading**: `config.py` uses it for file and CLI override merging
3. **Specification Merging**: Future features for spec composition

Example from agentic-spec:

```python
# In core.py
def resolve_inheritance(self, inherits: list[str]) -> dict[str, Any]:
    """Resolve inheritance chain and merge templates."""
    merged = {}
    for template_name in inherits:
        template = self.load_template(template_name)
        merged = merge_configs(merged, template)
    return merged
```

## Migration Guide

If you're replacing a simple recursive merge with this utility:

### Before:
```python
def simple_merge(a, b):
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            simple_merge(a[key], b[key])
        else:
            a[key] = b[key]
```

### After:
```python
from agentic_spec.utils.deep_merge import merge_configs

# Immutable, type-safe, configurable
result = merge_configs(a, b)
```

## Debugging Tips

1. **Enable Logging**: The utility logs warnings for skipped type mismatches
   ```python
   import logging
   logging.basicConfig(level=logging.WARNING)
   ```

2. **Use Path Information**: Errors show exact location of conflicts

3. **Test Incrementally**: For complex merges, test each level separately

4. **Validate Results**: For Pydantic models, merged results are always valid

## Summary

The deep merge utility provides a robust, production-ready solution for complex data structure merging. Its configurability, type safety, and comprehensive edge case handling make it suitable for configuration management, template inheritance, and any scenario requiring sophisticated data composition.

Key advantages over simple recursive merging:
- **Immutability**: No surprise mutations
- **Type Safety**: Configurable mismatch handling
- **Flexibility**: Multiple merge strategies
- **Reliability**: Comprehensive error handling
- **Maintainability**: Clear, documented behavior
