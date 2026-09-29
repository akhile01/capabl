import os

directory = r'c:\Users\Rajeev\capable agent b\capabl\frontend'
files = ['library.html', 'quiz.html', 'questions.html', 'progress.html']

for filename in files:
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    skip = False
    for line in lines:
        if line.startswith('<<<<<<< HEAD'):
            continue
        if line.startswith('======='):
            skip = True
            continue
        if line.startswith('>>>>>>>'):
            skip = False
            continue
        if not skip:
            if '<div class=\"nav-right\">' in line:
                out_lines.append(line)
                out_lines.append('            <button id=\"theme-toggle\" class=\"btn-tertiary\" style=\"padding: 6px 12px; font-size: 11px; margin-right: 12px;\">Toggle Theme</button>\n')
            else:
                out_lines.append(line)
                
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
