# Composable Decomposition Design

## Core Concept: Fractal Specifications

Every specification is a composable arrangement where:
- **Specs** contain **Tasks**
- **Tasks** can be **decomposed** into **Sub-specs** containing **Sub-tasks**
- This creates a fractal hierarchy: `Spec → Task → Sub-spec → Sub-task → Sub-sub-spec...`

## Mental Model Benefits

### 1. **Architectural Thinking**
- Forces consideration of natural decomposition boundaries
- Encourages proper abstraction layering
- Promotes clean separation of concerns

### 2. **Implementation Planning**
- Creates clear roadmap from high-level intent to concrete steps
- Enables parallel execution where dependencies allow
- Provides natural checkpoint and testing points

### 3. **Complexity Management**
- Breaks overwhelming tasks into manageable pieces
- Maintains context at appropriate abstraction levels
- Enables focused work sessions on atomic tasks

## Enhanced Prompt Engineering

### Spec Generation Improvements

**Current Issues:**
- Tasks often created without considering decomposability
- No guidance on appropriate granularity levels
- Missing hints about where/how tasks can be broken down

**Enhanced Approach:**
```
"implementation": [
  {
    "task": "Implement user authentication system",
    "details": "Create complete auth flow with JWT tokens...",
    "acceptance": "Users can login/logout, sessions persist...",
    "estimated_effort": "high",
    "decomposition_hint": "composite:can_split_by_component",
    "files": ["auth/", "middleware/", "tests/auth/"]
  },
  {
    "task": "Write unit tests for auth token validation",
    "details": "Test token parsing, expiration, signature validation...",
    "acceptance": "All edge cases covered, 100% test coverage...",
    "estimated_effort": "low",
    "decomposition_hint": "atomic",
    "files": ["tests/test_auth_tokens.py"]
  }
]
```

### Step Expansion Improvements

**Current Issues:**
- Focuses only on breaking down one step
- No consideration of composition integrity
- Missing verification that sub-tasks fully satisfy parent

**Enhanced Approach:**
```
PARENT TASK: "Implement user authentication system"
ACCEPTANCE: "Users can login/logout, sessions persist correctly"

DECOMPOSITION STRATEGY: By architectural component
↓
SUB-TASKS:
1. "Create JWT token generation/validation service"
   - Acceptance: "Tokens generated, validated, expired correctly"
   - Hint: "composite:can_split_by_feature" (generation vs validation)

2. "Implement login/logout API endpoints"
   - Acceptance: "Endpoints accept credentials, return tokens/success"
   - Hint: "atomic"

3. "Add authentication middleware for protected routes"
   - Acceptance: "Protected routes reject invalid tokens"
   - Hint: "atomic"

COMPOSITION VERIFICATION:
✓ Token service + endpoints + middleware = complete auth system
✓ All acceptance criteria map to parent acceptance
✓ No gaps (password reset not in parent scope)
✓ Appropriate abstraction (components, not implementation details)
```

## Implementation Strategy

### Phase 1: Enhanced Prompts
1. Update specification-generation.md with composability principles
2. Update step-expansion.md with composition integrity focus
3. Add decomposition_hint field to ImplementationStep model
4. Test with various complexity levels

### Phase 2: Tooling Enhancements
1. Add CLI command to suggest decomposition candidates
   `agentic-spec analyze-decomposition spec_id`
2. Enhance step expansion to verify composition integrity
3. Add visualization of task hierarchy and decomposition potential

### Phase 3: Advanced Features
1. Auto-suggest decomposition strategies based on task patterns
2. Composition verification warnings during spec generation
3. Effort estimation improvements based on decomposition analysis

## Decomposition Strategies Catalog

### By Architectural Component
- Frontend/Backend
- Service layers (API, Business, Data)
- Cross-cutting concerns (auth, logging, validation)

### By Data Flow Stage
- Input validation
- Core processing
- Output formatting
- Error handling

### By Implementation Phase
- Setup/scaffolding
- Core functionality
- Edge case handling
- Testing & validation
- Documentation

### By Feature Aspect
- Happy path implementation
- Error scenarios
- Performance optimization
- Security considerations
- User experience polish

## Composition Integrity Rules

### Completeness
- Union of all sub-task acceptances ⊇ parent acceptance
- No parent requirement left unaddressed
- No gaps in functionality coverage

### Boundedness
- Union of all sub-task acceptances ⊆ parent scope + reasonable decomposition overhead
- No feature creep beyond parent intent
- No sub-task exceeding parent abstraction level

### Cohesion
- Each sub-task represents a coherent unit of work
- Clear single responsibility for each sub-task
- Minimal coupling between sibling sub-tasks

### Testability
- Each sub-task should be independently verifiable
- Clear acceptance criteria at appropriate abstraction level
- Natural integration points between sub-tasks

## Example: Full Decomposition Hierarchy

```
SPEC: "Add real-time notifications to chat app"
├── TASK: "Design notification architecture" [composite:can_split_by_concern]
│   ├── SUB-SPEC: Architecture Design
│   │   ├── "Research WebSocket vs SSE approaches" [atomic]
│   │   ├── "Design message queue structure" [atomic]
│   │   └── "Create API contract for notifications" [atomic]
├── TASK: "Implement notification backend" [composite:can_split_by_component]
│   ├── SUB-SPEC: Backend Implementation
│   │   ├── "Create notification service" [composite:can_split_by_feature]
│   │   │   ├── SUB-SUB-SPEC: Service Implementation
│   │   │   │   ├── "Implement message publishing" [atomic]
│   │   │   │   └── "Implement message subscription" [atomic]
│   │   ├── "Add WebSocket connection management" [atomic]
│   │   └── "Integrate with existing chat message flow" [atomic]
└── TASK: "Update frontend for real-time display" [composite:can_split_by_component]
    └── SUB-SPEC: Frontend Updates
        ├── "Create notification UI components" [atomic]
        ├── "Add WebSocket client connection" [atomic]
        └── "Integrate notifications with chat UI" [atomic]
```

This approach transforms specifications from flat task lists into hierarchical, composable architectures that naturally guide implementation planning and execution.
