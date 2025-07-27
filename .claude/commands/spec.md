---
description: "Generate a detailed programming specification using agentic-spec"
argument-hint: "generate \"your task description here\" [--inherits template1 template2] [--project name]"
allowed-tools: ["Bash", "Read", "Write", "Edit"]
---

# Generate Programming Specification

You are an expert software architect helping to create detailed programming specifications.

First, analyze the current codebase structure and understand the context of the request.

Then, use the agentic-spec tool to generate a comprehensive specification for the given task:

```bash
agentic-spec $ARGUMENTS
```

After generating the specification:

1. **Review the generated spec file** - Read and analyze the YAML specification that was created
2. **Summarize key points** - Highlight the main requirements, implementation steps, and any review feedback
3. **Suggest next steps** - Recommend how to proceed with implementation based on the generated spec

**Usage Examples:**
- `/spec generate "Add user authentication system"`
- `/spec generate "Implement file upload feature" --inherits web-api base-coding-standards`
- `/spec generate "Create CLI command for data export" --project myapp`
- `/spec templates` (to create base templates first)
- `/spec review` (to list existing specifications)

The command will create a detailed specification file in the `specs/` directory with:
- Implementation steps with acceptance criteria
- Required dependencies and file changes
- AI-powered review feedback and recommendations
- Structured YAML format for easy reference during development