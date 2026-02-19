import sys
from pathlib import Path
from markdown_it import MarkdownIt

def convert_md_to_html(md_path, html_path):
    md_content = Path(md_path).read_text()
    md = MarkdownIt()
    html_content = md.render(md_content)
    
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
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .mermaid {{ display: none; }} /* Hide mermaid diagrams in simple HTML view unless rendered */
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    Path(html_path).write_text(full_html)
    print(f"Converted {md_path} to {html_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python convert.py <input_md> <output_html>")
        sys.exit(1)
    convert_md_to_html(sys.argv[1], sys.argv[2])
