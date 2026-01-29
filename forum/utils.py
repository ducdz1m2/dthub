import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from django.utils.safestring import mark_safe
from django.utils.html import escape
import re

class CodeHighlightExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.treeprocessors.register(CodeHighlightProcessor(md), 'codehighlight', 15)

class CodeHighlightProcessor(markdown.treeprocessors.Treeprocessor):
    def run(self, root):
        for element in root.iter('code'):
            if element.parent.tag == 'pre':
                # This is a code block
                code_text = element.text or ''
                
                # Extract language from class attribute
                lang = ''
                if 'class' in element.attrib:
                    classes = element.attrib['class'].split()
                    for cls in classes:
                        if cls.startswith('language-'):
                            lang = cls[9:]
                            break
                
                # Try to guess language if not specified
                if not lang and code_text.strip():
                    try:
                        lexer = guess_lexer(code_text)
                        lang = lexer.name.lower()
                    except:
                        lang = 'text'
                
                # Highlight the code
                try:
                    lexer = get_lexer_by_name(lang) if lang else get_lexer_by_name('text')
                    formatter = HtmlFormatter(
                        style='github-dark',
                        cssclass='highlight',
                        linenos='table',
                        hl_lines=[],
                        wrapcode=True,
                        cssstyles='background: #f6f8fa; border-radius: 6px;'
                    )
                    highlighted = highlight(code_text, lexer, formatter)
                    
                    # Create new HTML structure with copy button
                    html_with_copy = f"""
                    <div class="code-block-wrapper">
                        <div class="code-header">
                            <span class="code-language">{lang.upper()}</span>
                            <button class="copy-btn" onclick="copyCode(this)" title="Copy code">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                                </svg>
                                Copy
                            </button>
                        </div>
                        {highlighted}
                    </div>
                    """
                    
                    # Replace the parent pre element
                    parent = element.parent
                    parent.clear()
                    parent.append(markdown.util.etree.fromstring(f'<div>{html_with_copy}</div>'))
                    
                except:
                    # Fallback to escaped code
                    element.text = escape(code_text)

def render_markdown(content):
    """
    Convert markdown content to HTML with syntax highlighting
    """
    if not content:
        return ''
    
    # Configure markdown extensions
    extensions = [
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        CodeHighlightExtension(),
    ]
    
    # Convert markdown to HTML
    html = markdown.markdown(content, extensions=extensions)
    
    # Add responsive images and other enhancements
    html = re.sub(
        r'<img([^>]+)>',
        r'<img\1 class="img-fluid" loading="lazy">',
        html
    )
    
    # Wrap external links in new window
    html = re.sub(
        r'<a href="http([^"]*)"([^>]*)>',
        r'<a href="http\1"\2 target="_blank" rel="noopener noreferrer">',
        html
    )
    
    return mark_safe(html)

def get_markdown_preview_css():
    """
    Return CSS styles for markdown preview
    """
    formatter = HtmlFormatter(style='github-dark')
    return formatter.get_style_defs('.highlight')
