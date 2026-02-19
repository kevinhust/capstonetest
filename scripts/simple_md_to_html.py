import sys
import re
from pathlib import Path

def simple_md_to_html(md_path, html_path):
    md_content = Path(md_path).read_text()
    
    html_lines = []
    in_code_block = False
    
    for line in md_content.splitlines():
        # Code blocks
        if line.startswith("```"):
            if in_code_block:
                html_lines.append("</pre>")
                in_code_block = False
            else:
                html_lines.append("<pre>")
                in_code_block = True
            continue
        
        if in_code_block:
            html_lines.append(f"{line}")
            continue
            
        # Headers
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        # Lists
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        # Paragraphs (simple)
        elif line.strip():
            # Bold
            line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            # Italic
            line = re.sub(r'\*(.*?)\*', r'<i>\1</i>', line)
            # Links
            line = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', line)
            html_lines.append(f"<p>{line}</p>")
            
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Milestone 2 Report</title>
        <style>
            body {{ font-family: sans-serif; max-width: 800px; margin: 40px auto; line-height: 1.6; color: #333; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            code {{ background-color: #f4f4f4; padding: 2px 4px; border-radius: 4px; }}
            pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
            blockquote {{ border-left: 4px solid #ddd; padding-left: 10px; color: #666; }}
            li {{ margin-bottom: 5px; }}
            p {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        {''.join(html_lines)}
    </body>
    </html>
    """
    
    Path(html_path).write_text(full_html)
    print(f"Converted {md_path} to {html_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py <input_md> <output_html>")
        sys.exit(1)
    simple_md_to_html(sys.argv[1], sys.argv[2])
