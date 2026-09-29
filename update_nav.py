import os

directory = r'c:\Users\Rajeev\capable agent b\capabl\frontend'
files = ['index.html', 'library.html', 'quiz.html', 'questions.html', 'progress.html']

for filename in files:
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Replace logo with a link back to landing page
    content = content.replace('<div class="logo">AdaptEd</div>', '<a href="/" class="logo" style="text-decoration: none; color: inherit;">AdaptEd</a>')
    
    # Replace dashboard link
    content = content.replace('<a href="/" class="active">Dashboard</a>', '<a href="/dashboard" class="active">Dashboard</a>')
    content = content.replace('<a href="/">Dashboard</a>', '<a href="/dashboard">Dashboard</a>')
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated nav in {filename}")
