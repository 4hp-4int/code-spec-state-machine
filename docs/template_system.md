# Template System Documentation

## Overview

The agentic-spec template system provides a modular Jinja2-based templating solution for rendering programming specifications. It supports template inheritance, dynamic loading, and comprehensive validation.

## Features

- **Template Inheritance**: Use Jinja2's `{% extends %}` for modular template design
- **Dynamic Loading**: Load templates on-demand with error handling
- **Structure Validation**: Validate templates for correct syntax and inheritance
- **CLI Integration**: Manage templates through command-line interface

## Template Structure

### Base Template (`base_template.html`)

The base template defines the core structure with blocks that can be overridden:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Agentic Spec{% endblock %}</title>
    {% block head %}{% endblock %}
</head>
<body>
    <header>{% block header %}...{% endblock %}</header>
    <main>{% block content %}...{% endblock %}</main>
    <footer>{% block footer %}...{% endblock %}</footer>
</body>
</html>
```

### Child Template (`child_template.html`)

Child templates extend the base and override specific blocks:

```html
{% extends "base_template.html" %}

{% block title %}{{ metadata.id }} - Agentic Spec{% endblock %}

{% block head %}
<style>
    /* Custom styling */
</style>
{% endblock %}

{% block content %}
<div class="container">
    {{ super() }}
    <!-- Additional content -->
</div>
{% endblock %}
```

## Template Variables

Templates have access to the complete specification data structure:

- `metadata`: Specification metadata (id, version, status, etc.)
- `context`: Project context (project name, domain, dependencies)
- `requirements`: Functional and non-functional requirements
- `implementation`: Implementation steps and details
- `review_notes`: Review feedback and recommendations

### Example Variable Usage

```html
<!-- Display metadata -->
<h1>Specification: {{ metadata.id }}</h1>
<p>Status: {{ metadata.status }}</p>

<!-- Iterate over requirements -->
{% for req in requirements.functional %}
    <li>{{ req }}</li>
{% endfor %}

<!-- Conditional content -->
{% if review_notes %}
    <section class="review">
        {% for note in review_notes %}
            <p>{{ note }}</p>
        {% endfor %}
    </section>
{% endif %}
```

## CLI Commands

### Template Management

```bash
# List available templates
agentic-spec template list

# Show template information
agentic-spec template info --template base_template.html

# Validate all templates
agentic-spec validate

# Render specification with template
agentic-spec render <spec-id> --template child_template.html --output spec.html
```

### Template Validation

The validation system checks:

- **Syntax**: Valid Jinja2 syntax
- **Structure**: Required blocks present
- **Inheritance**: Parent templates exist and accessible
- **Variables**: Undeclared variables detected
- **Common Issues**: Hardcoded values, security concerns

Example validation output:

```
📊 Validation Results: 2/2 templates valid

✅ base_template.html
    Type: base
    Blocks: title, head, header, content, footer

✅ child_template.html
    Type: child
    Extends: base_template.html
    Blocks: title, head, content
```

## Programming Interface

### TemplateLoader

```python
from agentic_spec.template_loader import TemplateLoader

# Initialize loader
loader = TemplateLoader()

# List templates
templates = loader.list_available_templates()

# Load and render template
template = loader.load_template("child_template.html")
rendered = loader.render_template("child_template.html", spec_data)

# Check template existence
exists = loader.template_exists("my_template.html")
```

### TemplateValidator

```python
from agentic_spec.template_validator import TemplateValidator

# Initialize validator
validator = TemplateValidator()

# Validate single template
result = validator.validate_template("base_template.html")
print(f"Valid: {result['valid']}")
print(f"Errors: {result['errors']}")

# Validate all templates
results = validator.validate_all_templates()
```

## Creating Custom Templates

### Step 1: Create Template File

Create your template in the `agentic_spec/templates/` directory:

```html
<!-- my_custom_template.html -->
{% extends "base_template.html" %}

{% block title %}Custom Spec - {{ metadata.id }}{% endblock %}

{% block head %}
<link rel="stylesheet" href="custom.css">
{% endblock %}

{% block content %}
<div class="custom-layout">
    <h1>{{ context.project }}</h1>
    <!-- Custom content structure -->
    {{ super() }}
</div>
{% endblock %}
```

### Step 2: Validate Template

```bash
agentic-spec validate
```

### Step 3: Test Rendering

```bash
agentic-spec render <spec-id> --template my_custom_template.html
```

## Template Inheritance Best Practices

### 1. Define Clear Block Structure

```html
<!-- Base template should have logical blocks -->
{% block navigation %}{% endblock %}
{% block sidebar %}{% endblock %}
{% block main_content %}{% endblock %}
{% block scripts %}{% endblock %}
```

### 2. Use Meaningful Block Names

```html
<!-- Good: Descriptive names -->
{% block requirements_section %}{% endblock %}
{% block implementation_steps %}{% endblock %}

<!-- Avoid: Generic names -->
{% block content1 %}{% endblock %}
{% block div2 %}{% endblock %}
```

### 3. Provide Default Content

```html
<!-- Base template with sensible defaults -->
{% block footer %}
<p>&copy; {{ metadata.created[:4] }} Agentic Spec</p>
{% endblock %}
```

### 4. Use super() for Extension

```html
<!-- Child template extending parent content -->
{% block content %}
    {{ super() }}
    <div class="additional-content">
        <!-- Extra content -->
    </div>
{% endblock %}
```

## Error Handling

The template system provides comprehensive error handling:

### Template Not Found

```python
try:
    template = loader.load_template("nonexistent.html")
except TemplateNotFound:
    print("Template not found")
    # Available templates: loader.list_available_templates()
```

### Validation Errors

```python
result = validator.validate_template("template.html")
if not result['valid']:
    for error in result['errors']:
        print(f"Error: {error}")
```

### Rendering Errors

```bash
# CLI provides helpful error messages
❌ Error rendering template: Template 'missing.html' not found
💡 Use 'agentic-spec validate' to check template syntax
```

## Security Considerations

### Auto-Escaping

Templates use auto-escaping for HTML content:

```html
<!-- Safe: Automatically escaped -->
<p>{{ user_input }}</p>

<!-- Raw output (use carefully) -->
<p>{{ trusted_html | safe }}</p>
```

### Variable Validation

The validator warns about potentially unsafe patterns:

```
⚠️ Found 3 potentially unescaped variables
⚠️ Hardcoded HTTP URL found, consider using HTTPS or variable
```

## Integration with Workflow

### Auto-Rendering

Configure automatic template rendering in your workflow:

```yaml
# agentic_spec_config.yaml
workflow:
  auto_render: true
  default_template: "child_template.html"
  output_directory: "rendered_specs/"
```

### Custom Templates per Domain

```bash
# Domain-specific templates
agentic-spec render api-spec --template web_api_template.html
agentic-spec render cli-spec --template cli_template.html
```

## Troubleshooting

### Common Issues

1. **Template not found**: Check template name and directory
2. **Inheritance errors**: Ensure parent template exists
3. **Variable errors**: Check specification data structure
4. **Rendering fails**: Validate template syntax first

### Debug Commands

```bash
# Check available templates
agentic-spec template list

# Validate template structure
agentic-spec validate

# Test template with sample data
agentic-spec render <spec-id> --template <name>
```

### Logging

Enable debug logging for detailed template operations:

```python
import logging
logging.getLogger('agentic_spec.template_loader').setLevel(logging.DEBUG)
logging.getLogger('agentic_spec.template_validator').setLevel(logging.DEBUG)
```

## Examples

### Basic Rendering

```bash
# Render specification as HTML
agentic-spec render 462eb499 --output spec_462eb499.html
```

### Custom Template

```bash
# Use custom template
agentic-spec render 462eb499 --template custom.html --output custom_spec.html
```

### Batch Processing

```bash
# Render all specifications
for spec in specs/*.yaml; do
    id=$(basename "$spec" .yaml | cut -d'-' -f3)
    agentic-spec render "$id" --output "rendered/$id.html"
done
```

This template system provides a flexible, maintainable way to generate formatted output from your programming specifications while ensuring correctness through validation and proper error handling.