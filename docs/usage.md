# Usage Guide

## Getting Started

### Initial Setup

1. **Install the tool**:
   ```bash
   # From source
   git clone https://github.com/yourusername/agentic-spec.git
   cd agentic-spec
   make install-dev
   ```

2. **Set up your OpenAI API key**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   ```

3. **Initialize a new project**:
   ```bash
   agentic-spec init --project myproject
   ```

This creates the basic directory structure and configuration files you'll need.

## Core Workflows

### 1. Basic Specification Generation

**Simple generation**:
```bash
agentic-spec generate "Add user authentication to the API"
```

**With context customization**:
```bash
agentic-spec generate "Implement real-time notifications" \
  --user-role "senior developer" \
  --target-audience "team" \
  --complexity "advanced" \
  --tone "detailed"
```

**Interactive mode for complex prompts**:
```bash
agentic-spec generate
# Type your multi-line prompt, then press Ctrl+D (Unix) or Ctrl+Z (Windows)
```

### 2. Using Prompt Templates

Agentic-spec includes specialized prompt templates that tailor the AI's approach for different types of development tasks.

**Browse available templates**:
```bash
agentic-spec browse-templates
```

**Preview a specific template**:
```bash
agentic-spec preview-template feature-addition
```

**Generate with a specific template**:
```bash
# Use template directly
agentic-spec generate --template feature-addition "Add JWT authentication"

# Interactive template selection (if no --template provided)
agentic-spec generate "Add user management system"
# Will show template menu for selection
```

**Available template types**:
- `basic-specification` - Comprehensive specification generation with balanced detail and practicality
- `feature-addition` - Surgical feature integration with focus on clean architectural alignment
- `bug-fix` - Minimal-scope bug fixes with maximum safety and regression prevention
- `refactoring` - Safe incremental code improvements without functional changes

Templates provide context-aware prompts that help the AI understand the specific nature of your task, resulting in more targeted and relevant specifications.

### 3. Template Inheritance

**Using single template**:
```bash
agentic-spec generate "Add data export endpoints" --inherits web-api
```

**Using multiple templates**:
```bash
agentic-spec generate "Create admin dashboard" \
  --inherits web-api ui-components base-coding-standards
```

**List available templates**:
```bash
agentic-spec template list
```

### 4. Sub-specification Expansion

**List specifications**:
```bash
agentic-spec review
```

**Expand a specific implementation step**:
```bash
# Expand step 2 of specification abc12345
agentic-spec expand abc12345:2
```

**View specification relationships**:
```bash
agentic-spec graph
```

### 5. Configuration Management

**Show current configuration**:
```bash
agentic-spec config show
```

**Override settings dynamically**:
```bash
agentic-spec generate "task" --set prompt_settings.temperature=0.2
agentic-spec generate "task" --set workflow.auto_review=false
```

## Input Methods

### Command Line Arguments
```bash
agentic-spec generate "Build a REST API for product management"
```

### Piped Input
```bash
echo "Add rate limiting to API endpoints" | agentic-spec generate
cat requirements.txt | agentic-spec generate
```

### Interactive Input
```bash
agentic-spec generate
# Enter multi-line prompt:
# Build a comprehensive user management system with:
# - User registration and authentication
# - Profile management
# - Role-based access control
# - Password reset functionality
# [Ctrl+D to finish]
```

### File Input
```bash
agentic-spec generate "$(cat feature-description.md)"
```

## Advanced Features

### Dry Run Mode
Preview what would be generated without saving:
```bash
agentic-spec generate "Add caching layer" --dry-run
```

### Custom Directories
```bash
agentic-spec generate "task" \
  --spec-templates-dir ./custom-templates \
  --specs-dir ./project-specs
```

### Feedback Collection
Enable interactive feedback during generation:
```bash
agentic-spec generate "task" --feedback
```

## Template System

### Using Pre-built Templates

**Web API development**:
```bash
agentic-spec generate "Add OAuth2 authentication" --inherits web-api
```

**CLI application**:
```bash
agentic-spec generate "Add progress bars and logging" --inherits cli-application
```

**Data analysis**:
```bash
agentic-spec generate "Create sales dashboard" --inherits data-analysis
```

**Machine learning**:
```bash
agentic-spec generate "Build recommendation system" --inherits machine-learning
```

### Creating Custom Templates

1. **Create a template file**:
   ```yaml
   # spec-templates/my-custom-template.yaml
   domain: "my domain"
   dependencies:
     - name: "custom-lib"
       version: "1.0.0"
       description: "My custom library"
   patterns:
     architecture: "Custom architecture pattern"
     testing: "Custom testing approach"
   files_involved:
     - "src/"
     - "tests/"
   ```

2. **Use the custom template**:
   ```bash
   agentic-spec generate "task" --inherits my-custom-template
   ```

### Template Information
```bash
# Show template details
agentic-spec template info --template web-api

# Validate all templates
agentic-spec validate
```

## Configuration Options

### Configuration File (`agentic_spec_config.yaml`)

```yaml
# AI Provider Settings
ai_settings:
  default_provider: "openai"
  providers:
    openai:
      provider_type: "openai"
      default_model: "gpt-4o-mini"
      timeout: 120.0

# Generation Settings
prompt_settings:
  temperature: 0.1        # Lower = more deterministic
  max_tokens: 1300        # Response length limit
  enable_web_search: true # Use web search for current practices

# Default Context Parameters
default_context:
  user_role: "solo developer"
  target_audience: "solo developer"
  desired_tone: "practical"
  complexity_level: "intermediate"
  time_constraints: "production ready"

# Workflow Settings
workflow:
  auto_review: true              # Generate AI review automatically
  collect_feedback: false        # Don't prompt for feedback by default
  save_intermediate_steps: true  # Save generation steps

# Directory Settings
directories:
  spec_templates_dir: "spec-templates"
  prompt_templates_dir: "prompt-templates"
  specs_dir: "specs"
```

### Environment Variables

```bash
# Required
export OPENAI_API_KEY=your-api-key-here

# Optional
export AGENTIC_SPEC_CONFIG=path/to/custom-config.yaml
```

### CLI Overrides

Override any configuration setting:
```bash
agentic-spec generate "task" \
  --set prompt_settings.temperature=0.5 \
  --set workflow.auto_review=false \
  --set default_context.complexity_level=simple
```

## Specification Management

### Viewing Specifications

**List all specifications**:
```bash
agentic-spec review
```

**View dependency graph**:
```bash
agentic-spec graph
```

### Status Management

**Mark specification as implemented**:
```bash
agentic-spec publish abc12345
```

**Complete workflow (commit changes and publish)**:
```bash
make spec-complete
```

### Working with Sub-specifications

**Expand complex steps**:
```bash
# View the specification first
agentic-spec review

# Expand a specific step
agentic-spec expand abc12345:1
```

Sub-specifications are automatically linked to their parent specifications.

## Common Use Cases

### Web API Development

**Initial API setup**:
```bash
agentic-spec generate "Create REST API for e-commerce platform" \
  --inherits web-api base-coding-standards \
  --complexity intermediate
```

**Add authentication**:
```bash
agentic-spec generate "Add JWT-based authentication" \
  --inherits web-api security \
  --tone detailed
```

**Add specific features**:
```bash
agentic-spec generate "Implement order management endpoints" \
  --inherits web-api \
  --target-audience "team"
```

### CLI Application Development

**Core CLI structure**:
```bash
agentic-spec generate "Build file processing CLI tool" \
  --inherits cli-application \
  --complexity simple
```

**Add advanced features**:
```bash
agentic-spec generate "Add configuration system and plugins" \
  --inherits cli-application \
  --complexity advanced
```

### Data Analysis Projects

**Data pipeline**:
```bash
agentic-spec generate "ETL pipeline for sales data analysis" \
  --inherits data-analysis \
  --user-role "data engineer"
```

**Visualization**:
```bash
agentic-spec generate "Interactive dashboard with real-time updates" \
  --inherits data-analysis \
  --complexity advanced
```

### Machine Learning Projects

**Model development**:
```bash
agentic-spec generate "Customer churn prediction model" \
  --inherits machine-learning data-analysis \
  --complexity intermediate
```

**Model deployment**:
```bash
agentic-spec generate "Deploy model as REST API service" \
  --inherits machine-learning web-api \
  --tone production-ready
```

## Output Format and Structure

### Specification Structure

Generated specifications follow this YAML structure:

```yaml
metadata:
  id: "abc12345"                    # Unique identifier
  title: "Add JWT authentication"   # Human-readable title
  inherits: ["web-api", "security"] # Template inheritance chain
  created: "2025-07-27T10:30:00"    # Creation timestamp
  version: "1.0"                    # Specification version
  status: "draft"                   # draft|implemented|published
  parent_spec_id: null              # Parent if this is a sub-spec
  child_spec_ids: ["def67890"]      # Child sub-specifications

context:
  project: "ecommerce-api"          # Project name
  domain: "web API development"     # Problem domain
  dependencies:                     # Required dependencies
    - name: "pyjwt"
      version: "2.8.0"
      description: "JWT token handling"
  files_involved:                   # Files to create/modify
    - "auth/middleware.py"
    - "tests/test_auth.py"

requirements:
  functional:                       # What the feature should do
    - "Generate JWT tokens on login"
    - "Validate tokens on protected routes"
  non_functional:                   # Performance, security, etc.
    - "Token validation < 10ms"
    - "Secure token storage"
  constraints:                      # Limitations and requirements
    - "Use existing user model"
    - "Maintain API compatibility"

implementation:                     # Step-by-step tasks
  - task: "Create JWT middleware"
    details: "FastAPI dependency for JWT validation..."
    files: ["auth/middleware.py"]
    acceptance: "Middleware validates tokens correctly"
    estimated_effort: "medium"      # low|medium|high
    step_id: "abc12345:0"          # Unique step identifier
    sub_spec_id: null              # Link to sub-specification

review_notes:                       # AI-generated feedback
  - "Consider refresh token strategy"
  - "Add rate limiting to auth endpoints"

context_parameters:                 # Generation context
  user_role: "solo developer"
  target_audience: "team"
  desired_tone: "practical"
  complexity_level: "intermediate"
```

### Understanding Implementation Steps

Each implementation step includes:

- **Task**: Brief description of what to do
- **Details**: Comprehensive explanation with specific guidance
- **Files**: Which files to create or modify
- **Acceptance**: How to know when the step is complete
- **Estimated effort**: Rough effort estimate (low/medium/high)
- **Step ID**: Unique identifier for sub-specification expansion
- **Sub-spec ID**: Link to expanded sub-specification (if any)

## Troubleshooting

### Common Issues

**API Key Problems**:
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Set temporarily
export OPENAI_API_KEY=your-key-here

# Add to shell profile (bash)
echo 'export OPENAI_API_KEY=your-key-here' >> ~/.bashrc
source ~/.bashrc

# Add to shell profile (zsh)
echo 'export OPENAI_API_KEY=your-key-here' >> ~/.zshrc
source ~/.zshrc
```

**Template Not Found**:
```bash
# Check available templates
agentic-spec template list

# Recreate base templates
agentic-spec templates --project myproject

# Check template directory
ls spec-templates/
```

**Configuration Issues**:
```bash
# Validate current configuration
agentic-spec config validate

# Show configuration with sources
agentic-spec config show

# Reset to defaults
agentic-spec config init --force
```

**Generation Failures**:
```bash
# Try with simpler prompt
agentic-spec generate "simple task description"

# Use dry-run to debug
agentic-spec generate "task" --dry-run

# Check AI provider status
agentic-spec config show | grep ai_settings
```

### Platform-Specific Issues

**Windows Path Issues**:
- Use forward slashes: `--specs-dir specs/output`
- Quote paths with spaces: `--specs-dir "my specs"`
- Set Git line endings: `git config core.autocrlf true`

**PowerShell Issues**:
- Use double quotes for prompts: `agentic-spec generate "my task"`
- Escape special characters: `agentic-spec generate "task with `$variable"`

**Unix Shell Issues**:
- Single quotes preserve literal strings: `agentic-spec generate 'task with $variables'`
- Use backslash to escape: `agentic-spec generate "task with \$variable"`

### Performance Optimization

**Faster Generation**:
```bash
# Use lower temperature for faster, more deterministic results
agentic-spec generate "task" --set prompt_settings.temperature=0.1

# Disable web search for faster responses
agentic-spec generate "task" --set prompt_settings.enable_web_search=false

# Use shorter token limit
agentic-spec generate "task" --set prompt_settings.max_tokens=800
```

**Reduce API Costs**:
- Use `--dry-run` to preview before generating
- Set lower `max_tokens` in configuration
- Use simpler prompts when appropriate
- Cache common templates locally

## Best Practices

### Writing Effective Prompts

**Be Specific**:
```bash
# Good
agentic-spec generate "Add JWT authentication middleware with refresh tokens and role-based permissions"

# Less good
agentic-spec generate "Add auth"
```

**Provide Context**:
```bash
agentic-spec generate "Add Redis caching layer for frequently accessed user data in the FastAPI application"
```

**Use Templates Appropriately**:
```bash
# For web APIs
agentic-spec generate "Add data validation" --inherits web-api

# For CLI tools
agentic-spec generate "Add logging system" --inherits cli-application
```

### Template Management

**Start with Base Templates**:
1. Use pre-built templates for common scenarios
2. Create project-specific templates for repeated patterns
3. Maintain template documentation

**Template Inheritance Strategy**:
- Use broad templates (like `base-coding-standards`) for consistency
- Use specific templates (like `web-api`) for domain patterns
- Combine templates for complex scenarios

### Specification Workflow

1. **Generate** initial specification
2. **Review** AI feedback and requirements
3. **Expand** complex steps into sub-specifications
4. **Implement** following the specification
5. **Publish** when complete

### Integration with Development Workflow

**Git Integration**:
- Commit specifications before implementation
- Reference specification IDs in commit messages
- Use specification status to track progress

**Documentation**:
- Specifications serve as implementation documentation
- Link specifications to pull requests
- Use review notes for code review guidance

**Team Collaboration**:
- Share specifications before implementation
- Use specifications for task assignment
- Update specifications when requirements change

This usage guide covers the most common scenarios and workflows. For advanced use cases or integration with specific development environments, refer to the API reference and examples in the repository.
