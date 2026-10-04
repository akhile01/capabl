import os
import glob

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
html_files = glob.glob(os.path.join(frontend_dir, "*.html"))

head_tags = '<link rel="stylesheet" href="/static/theme.css">\n    <script src="/static/theme.js"></script>\n'
button_html = '''
            <button class="theme-toggle" aria-label="Toggle Theme">
                <span class="icon-light">☀️</span>
                <span class="icon-dark">🌙</span>
            </button>'''

for filepath in html_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add head tags if not present
    if "theme.css" not in content:
        content = content.replace("</head>", f"    {head_tags}</head>")

    # Add button to nav-right
    if '<div class="nav-right">' in content and "theme-toggle" not in content:
        content = content.replace('<div class="nav-right">', f'<div class="nav-right">{button_html}')
        
    # Add button to landing-nav-links in landing.html
    if '<div class="landing-nav-links">' in content and "theme-toggle" not in content:
        content = content.replace('<div class="landing-nav-links">', f'<div class="landing-nav-links">{button_html}')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Updated all HTML files!")
