from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='format_paper_content')
def format_paper_content(content):
    """
    Format paper content to look like a professional research paper.
    Adds proper structure, section headers, and formatting.
    """
    if not content:
        return ""
    
    # Split content into lines
    lines = content.split('\n')
    formatted_lines = []
    
    # Track if we're in specific sections
    in_abstract = False
    in_introduction = False
    in_conclusion = False
    in_references = False
    section_number = 1
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Detect and format section headers
        if re.match(r'^(abstract|summary)', line.lower()):
            formatted_lines.append('<div class="abstract">')
            formatted_lines.append(f'<p>{line}</p>')
            in_abstract = True
            continue
            
        if re.match(r'^(introduction)', line.lower()):
            if in_abstract:
                formatted_lines.append('</div>')
                in_abstract = False
            formatted_lines.append('<div class="introduction">')
            formatted_lines.append(f'<h2>{line}</h2>')
            in_introduction = True
            continue
            
        if re.match(r'^(conclusion|conclusions|summary|discussion)', line.lower()):
            if in_introduction:
                formatted_lines.append('</div>')
                in_introduction = False
            formatted_lines.append('<div class="section">')
            formatted_lines.append(f'<h2 class="section-header">{line}</h2>')
            continue
            
        if re.match(r'^(references|bibliography|works\s+cited)', line.lower()):
            if in_introduction:
                formatted_lines.append('</div>')
                in_introduction = False
            formatted_lines.append('<div class="references">')
            formatted_lines.append(f'<h2>{line}</h2>')
            in_references = True
            continue
            
        # Detect numbered sections (1., 2., 3., etc.)
        if re.match(r'^\d+\.', line):
            if in_introduction:
                formatted_lines.append('</div>')
                in_introduction = False
            formatted_lines.append('<div class="section">')
            formatted_lines.append(f'<h3 class="section-header">{line}</h3>')
            section_number += 1
            continue
            
        # Detect subsection headers (2.1, 2.2, etc.)
        if re.match(r'^\d+\.\d+', line):
            formatted_lines.append(f'<h4>{line}</h4>')
            continue
            
        # Format regular paragraphs
        if line:
            # Check if this looks like a paragraph start
            if len(line) > 50 and not line.startswith('•') and not line.startswith('-'):
                formatted_lines.append(f'<p>{line}</p>')
            else:
                # Handle lists and short lines
                if line.startswith('•') or line.startswith('-'):
                    formatted_lines.append(f'<li>{line[1:].strip()}</li>')
                else:
                    formatted_lines.append(f'<p>{line}</p>')
    
    # Close any open sections
    if in_abstract:
        formatted_lines.append('</div>')
    if in_introduction:
        formatted_lines.append('</div>')
    if in_references:
        formatted_lines.append('</div>')
    
    # Join all formatted lines
    formatted_content = '\n'.join(formatted_lines)
    
    # Clean up any double line breaks
    formatted_content = re.sub(r'\n\s*\n', '\n', formatted_content)
    
    return mark_safe(formatted_content)

@register.filter(name='add_paper_structure')
def add_paper_structure(content):
    """
    Add paper structure elements like page breaks and better organization.
    """
    if not content:
        return ""
    
    # Add page break before references if not already present
    if 'references' in content.lower() or 'bibliography' in content.lower():
        content = re.sub(
            r'(references|bibliography|works\s+cited)',
            r'<div class="page-break"></div>\1',
            content,
            flags=re.IGNORECASE
        )
    
    return mark_safe(content)
