// Markdown Editor with Live Preview and Syntax Highlighting
class MarkdownEditor {
    constructor(textarea, preview = null) {
        this.textarea = textarea;
        this.preview = preview;
        this.converter = new showdown.Converter({
            tables: true,
            strikethrough: true,
            tasklists: true,
            ghCodeBlocks: true,
            emoji: true,
            underline: true,
            highlightSyntax: true
        });
        
        this.init();
    }
    
    init() {
        // Create toolbar
        this.createToolbar();
        
        // Setup live preview
        if (this.preview) {
            this.textarea.addEventListener('input', () => this.updatePreview());
            this.updatePreview();
        }
        
        // Setup tab key for code indentation
        this.textarea.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Auto-resize textarea
        this.autoResize();
    }
    
    createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'markdown-toolbar btn-toolbar mb-2';
        toolbar.innerHTML = `
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="bold" title="Bold (Ctrl+B)">
                    <i class="fas fa-bold"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="italic" title="Italic (Ctrl+I)">
                    <i class="fas fa-italic"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="strikethrough" title="Strikethrough">
                    <i class="fas fa-strikethrough"></i>
                </button>
            </div>
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="heading" title="Heading">
                    <i class="fas fa-heading"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="quote" title="Quote">
                    <i class="fas fa-quote-left"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="code" title="Inline Code">
                    <i class="fas fa-code"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="codeblock" title="Code Block">
                    <i class="fas fa-file-code"></i>
                </button>
            </div>
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="ul" title="Unordered List">
                    <i class="fas fa-list-ul"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="ol" title="Ordered List">
                    <i class="fas fa-list-ol"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="tasklist" title="Task List">
                    <i class="fas fa-tasks"></i>
                </button>
            </div>
            <div class="btn-group me-2" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="link" title="Link">
                    <i class="fas fa-link"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="image" title="Image">
                    <i class="fas fa-image"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="table" title="Table">
                    <i class="fas fa-table"></i>
                </button>
            </div>
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="preview" title="Toggle Preview">
                    <i class="fas fa-eye"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-action="help" title="Markdown Help">
                    <i class="fas fa-question-circle"></i>
                </button>
            </div>
        `;
        
        this.textarea.parentNode.insertBefore(toolbar, this.textarea);
        
        // Add event listeners to toolbar buttons
        toolbar.addEventListener('click', (e) => {
            const button = e.target.closest('button');
            if (button) {
                e.preventDefault();
                this.handleToolbarAction(button.dataset.action);
            }
        });
    }
    
    handleToolbarAction(action) {
        const start = this.textarea.selectionStart;
        const end = this.textarea.selectionEnd;
        const text = this.textarea.value;
        const selectedText = text.substring(start, end);
        
        let replacement = '';
        let cursorOffset = 0;
        
        switch (action) {
            case 'bold':
                replacement = `**${selectedText || 'bold text'}**`;
                cursorOffset = selectedText ? 0 : -5;
                break;
            case 'italic':
                replacement = `*${selectedText || 'italic text'}*`;
                cursorOffset = selectedText ? 0 : -6;
                break;
            case 'strikethrough':
                replacement = `~~${selectedText || 'strikethrough text'}~~`;
                cursorOffset = selectedText ? 0 : -9;
                break;
            case 'heading':
                replacement = `## ${selectedText || 'Heading'}`;
                cursorOffset = selectedText ? 0 : -3;
                break;
            case 'quote':
                replacement = `> ${selectedText || 'Quote'}`;
                cursorOffset = selectedText ? 0 : -2;
                break;
            case 'code':
                replacement = `\`${selectedText || 'code'}\``;
                cursorOffset = selectedText ? 0 : -2;
                break;
            case 'codeblock':
                replacement = `\`\`\`python\n${selectedText || '// Your code here'}\n\`\`\``;
                cursorOffset = selectedText ? 0 : -6;
                break;
            case 'ul':
                replacement = `- ${selectedText || 'List item'}`;
                cursorOffset = selectedText ? 0 : -2;
                break;
            case 'ol':
                replacement = `1. ${selectedText || 'List item'}`;
                cursorOffset = selectedText ? 0 : -4;
                break;
            case 'tasklist':
                replacement = `- [ ] ${selectedText || 'Task item'}`;
                cursorOffset = selectedText ? 0 : -6;
                break;
            case 'link':
                replacement = `[${selectedText || 'Link text'}](url)`;
                cursorOffset = selectedText ? -5 : -9;
                break;
            case 'image':
                replacement = `![${selectedText || 'Alt text'}](image-url)`;
                cursorOffset = selectedText ? -11 : -15;
                break;
            case 'table':
                replacement = `| Header 1 | Header 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |`;
                cursorOffset = -20;
                break;
            case 'preview':
                this.togglePreview();
                return;
            case 'help':
                this.showHelp();
                return;
        }
        
        this.textarea.value = text.substring(0, start) + replacement + text.substring(end);
        this.textarea.selectionStart = this.textarea.selectionEnd = start + replacement.length + cursorOffset;
        this.textarea.focus();
        
        this.updatePreview();
        this.autoResize();
    }
    
    handleKeyDown(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.textarea.selectionStart;
            const end = this.textarea.selectionEnd;
            const text = this.textarea.value;
            
            this.textarea.value = text.substring(0, start) + '    ' + text.substring(end);
            this.textarea.selectionStart = this.textarea.selectionEnd = start + 4;
            
            this.updatePreview();
        }
    }
    
    updatePreview() {
        if (!this.preview) return;
        
        const markdown = this.textarea.value;
        const html = this.converter.makeHtml(markdown);
        
        // Add syntax highlighting to code blocks
        this.preview.innerHTML = this.addSyntaxHighlighting(html);
        
        // Add copy buttons to code blocks
        this.addCopyButtons();
    }
    
    addSyntaxHighlighting(html) {
        // This would typically use a library like Prism.js or highlight.js
        // For now, return the HTML as-is
        return html;
    }
    
    addCopyButtons() {
        const codeBlocks = this.preview.querySelectorAll('pre code');
        codeBlocks.forEach((block) => {
            if (!block.parentElement.querySelector('.copy-btn')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                
                const header = document.createElement('div');
                header.className = 'code-header';
                
                const lang = block.className.replace('language-', '').toUpperCase() || 'CODE';
                const langSpan = document.createElement('span');
                langSpan.className = 'code-language';
                langSpan.textContent = lang;
                
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-btn';
                copyBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copy
                `;
                copyBtn.onclick = () => this.copyCode(block);
                
                header.appendChild(langSpan);
                header.appendChild(copyBtn);
                
                const pre = block.parentElement;
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(header);
                wrapper.appendChild(pre);
            }
        });
    }
    
    copyCode(codeBlock) {
        const text = codeBlock.textContent;
        navigator.clipboard.writeText(text).then(() => {
            const btn = codeBlock.parentElement.parentElement.querySelector('.copy-btn');
            const originalHTML = btn.innerHTML;
            btn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                    Copied!
                `;
            btn.classList.add('copied');
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('copied');
            }, 2000);
        });
    }
    
    togglePreview() {
        if (this.preview) {
            this.preview.style.display = this.preview.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    showHelp() {
        const helpText = `
# Markdown Help

## Basic Syntax
- **Bold text**: \`**text**\`
- *Italic text*: \`*text*\`
- ~~Strikethrough~~: \`~~text~~\`
- \`Inline code\`: \\\`code\\\`

## Headers
# Heading 1
## Heading 2
### Heading 3

## Lists
- Unordered list item 1
- Unordered list item 2

1. Ordered list item 1
2. Ordered list item 2

- [ ] Task list item
- [x] Completed task

## Code Blocks
\`\`\`python
def hello():
    print("Hello, World!")
\`\`\`

## Links and Images
[Link text](https://example.com)
![Alt text](image-url)

## Tables
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |

## Quotes
> This is a quote
> This is another quote line
        `;
        
        alert(helpText);
    }
    
    autoResize() {
        this.textarea.style.height = 'auto';
        this.textarea.style.height = this.textarea.scrollHeight + 'px';
    }
}

// Global function for copy buttons
function copyCode(button) {
    const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
    const text = codeBlock.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Copied!
        `;
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    });
}

// Initialize markdown editors
document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('.markdown-editor');
    textareas.forEach(textarea => {
        const previewId = textarea.dataset.preview;
        const preview = previewId ? document.getElementById(previewId) : null;
        new MarkdownEditor(textarea, preview);
    });
});
