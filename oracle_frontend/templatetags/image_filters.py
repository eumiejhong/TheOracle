import base64
import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='b64encode')
def b64encode(value):
    return base64.b64encode(value).decode()

@register.filter(name='strip_markdown')
def strip_markdown(value):
    """Remove markdown formatting and convert to clean prose."""
    if not value:
        return value
    
    text = str(value)
    
    # Remove entire lines that are just headers like "**Outfit Breakdown:**" or "Outfit Breakdown:"
    text = re.sub(r'^\s*\*?\*?[A-Za-z\s]+(?:Breakdown|Concept|Summary|Details|Items):\*?\*?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    # Remove bold markers **text**
    text = re.sub(r'\*\*([^*]+)\*\*:?', r'\1', text)
    # Remove italic markers *text*
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # Remove header markers (# ## ###)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove bullet points and their category labels (- Outerwear: Item becomes just Item)
    text = re.sub(r'^\s*[-*]\s*[A-Za-z]+:\s*', '', text, flags=re.MULTILINE)
    # Remove remaining bullet points
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered lists (1. item)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove standalone category labels at line start
    text = re.sub(r'^[A-Z][a-z]+:\s+', '', text, flags=re.MULTILINE)
    # Remove underscores used for emphasis
    text = re.sub(r'_([^_]+)_', r'\1', text)
    # Remove backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Collapse multiple newlines into double newlines
    text = re.sub(r'\n{2,}', '\n\n', text)
    # Remove lines that are just whitespace
    text = re.sub(r'^\s*$\n', '', text, flags=re.MULTILINE)
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text