# Model Validation Test Design

## Overview
Comprehensive test cases for all Pydantic models after refactoring from dataclass to BaseModel.

## Test Structure
Each model will have a test class with the following test methods:
1. `test_valid_minimal` - Create with only required fields
2. `test_valid_complete` - Create with all fields populated
3. `test_missing_required` - Validation error for missing required fields
4. `test_invalid_types` - Type validation for each field
5. `test_field_constraints` - Field-specific constraints (min/max, patterns, etc.)
6. `test_extra_fields` - Behavior with extra fields based on ConfigDict
7. `test_model_dump_json` - Serialization with enums and complex types

## Enum Tests

### TaskStatus
- Valid values: PENDING, IN_PROGRESS, COMPLETED, BLOCKED, APPROVED, REJECTED, OVERRIDE
- Invalid enum test

### ApprovalLevel
- Valid values: PEER, LEAD, ADMIN
- Invalid enum test

### SpecStatus
- Valid values: DRAFT, REVIEWED, APPROVED, REJECTED, IMPLEMENTED, ARCHIVED
- Invalid enum test

### WorkflowStatus
- Valid values: 10 different statuses
- Invalid enum test

## Model Test Cases

### 1. DependencyModel
**Fields**: name (str), version (Optional[str]), description (Optional[str])
- ✅ Valid minimal: name only
- ✅ Valid complete: all fields
- ❌ Missing name: ValidationError
- ❌ Invalid types: name=123
- ✅ Extra fields allowed (ConfigDict extra="allow")

### 2. SpecMetadata
**Fields**: id, title, inherits, created, version, status, parent_spec_id, child_spec_ids, author, last_modified
- ✅ Valid minimal: required fields only
- ✅ Valid complete: all fields including lists
- ❌ Missing id/title: ValidationError
- ❌ Invalid status enum
- ❌ Invalid datetime formats
- ✅ Empty lists for inherits/child_spec_ids

### 3. SpecContext
**Fields**: project, domain, dependencies, affected_files
- ✅ Valid minimal: empty lists
- ✅ Valid complete: with dependencies and files
- ❌ Invalid dependency objects
- ✅ Nested validation for DependencyModel items

### 4. SpecRequirement
**Fields**: functional, non_functional, constraints
- ✅ Valid minimal: empty lists
- ✅ Valid complete: populated lists
- ❌ Non-list types for fields

### 5. TaskProgress
**Fields**: status, started_at, completed_at, assigned_to, time_spent_minutes, notes, blockers, rating, feedback
- ✅ Valid minimal: default status=PENDING
- ✅ Valid complete: all fields
- ❌ Invalid status enum
- ❌ Invalid rating (must be 1-5 or None)
- ❌ Negative time_spent_minutes
- ✅ Optional fields as None

### 6. ApprovalRecord
**Fields**: level, approved_by, approved_at, comments, override_reason
- ✅ Valid minimal: required fields only
- ✅ Valid complete: with override_reason
- ❌ Missing required fields
- ❌ Invalid approval level enum
- ❌ Invalid datetime

### 7. ImplementationStep
**Fields**: task, details, files, acceptance, estimated_effort, step_id, sub_spec_id, decomposition_hint, progress, approvals
- ✅ Valid minimal: required fields only
- ✅ Valid complete: with progress and approvals
- ❌ Missing task: ValidationError
- ✅ Nested validation for TaskProgress
- ✅ List of ApprovalRecord objects

### 8. ContextParameters
**Fields**: user_role, target_audience, desired_tone, complexity_level, time_constraints, existing_codebase_context, custom_parameters
- ✅ Valid minimal: with defaults
- ✅ Valid complete: all fields
- ✅ Empty dict for custom_parameters

### 9. FeedbackData
**Fields**: reviewer, feedback_type, content, severity, timestamp, resolved
- ✅ Valid minimal: required fields
- ✅ Valid complete: all fields
- ❌ Missing required fields
- ✅ Boolean field validation

### 10. WorkLogEntry
**Fields**: timestamp, user, action, details, task_id, duration_minutes
- ✅ Valid minimal: required fields
- ✅ Valid complete: with duration
- ❌ Missing required fields
- ❌ Negative duration
- ✅ Optional duration field

### 11. ProgrammingSpec (Complex)
**Fields**: metadata, context, requirements, implementation, review_notes, context_parameters, feedback_history, work_logs
- ✅ Valid minimal: required nested objects
- ✅ Valid complete: all fields populated
- ❌ Invalid nested objects
- ✅ Complex nested validation
- ✅ Lists of complex objects
- ✅ model_dump with mode='json'

### 12. Database Models (SpecificationDB, TaskDB, ApprovalDB, WorkLogDB)
**Common patterns**:
- Required id field
- Timestamp fields
- Status enums
- Field constraints
- ✅ Valid database records
- ❌ Missing required fields
- ❌ Invalid field constraints

## Special Test Cases

### Pydantic v2 Features
1. **model_dump() modes**:
   - Default mode
   - mode='json' for enum serialization
   - exclude_none=True

2. **model_validate()**:
   - Round-trip validation
   - From dict validation

3. **ConfigDict behavior**:
   - extra='allow' models
   - Field validation

### Edge Cases
1. **Empty strings vs None**:
   - Required string fields with ""
   - Optional string fields with ""

2. **List handling**:
   - Empty lists
   - Lists with invalid items
   - Lists with None values

3. **Datetime handling**:
   - String to datetime parsing
   - Timezone awareness
   - Invalid formats

4. **Numeric constraints**:
   - rating: 1-5 range
   - time/duration: >= 0
   - Boundary testing

## Test Implementation Plan

1. Create `test_model_validation.py`
2. Organize by model complexity:
   - Simple models first (enums, basic models)
   - Complex nested models last
3. Use pytest.parametrize for multiple test cases
4. Use fixtures for common test data
5. Clear error messages for debugging

## Coverage Goals
- 100% model coverage
- All validation rules tested
- All field constraints verified
- Edge cases covered
- Pydantic v2 features tested
