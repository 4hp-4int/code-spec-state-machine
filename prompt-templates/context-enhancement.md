CONTEXT PARAMETERS:
{% for section in context_sections -%}
- {{ section }}
{% endfor %}

TASK:
{{ base_prompt }}

Please consider the above context parameters when generating your response to ensure maximum relevance and accuracy for the specified user and situation.
