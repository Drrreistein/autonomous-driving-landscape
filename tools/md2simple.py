#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Markdown 渲染成极简 HTML（单栏、无装饰、README 风格）。"""
import sys, os, re

try:
    import markdown
except ImportError:
    sys.exit("need: pip install markdown")

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{
    max-width: 760px;
    margin: 0 auto;
    padding: 48px 24px 80px;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    font-size: 16px;
    line-height: 1.85;
    color: #222;
    background: #fff;
  }}
  h1 {{ font-size: 1.9em; font-weight: 600; margin: 0 0 .6em; line-height: 1.35; }}
  h2 {{ font-size: 1.32em; font-weight: 600; margin: 2.2em 0 .7em; padding-bottom: .25em; border-bottom: 1px solid #e8e8e8; }}
  h3 {{ font-size: 1.1em; font-weight: 600; margin: 1.6em 0 .5em; }}
  p {{ margin: .9em 0; }}
  blockquote {{
    margin: 1.2em 0; padding: .2em 1em;
    border-left: 3px solid #ddd; color: #555;
  }}
  blockquote p {{ margin: .5em 0; }}
  ul, ol {{ padding-left: 1.4em; margin: .9em 0; }}
  li {{ margin: .35em 0; }}
  table {{
    border-collapse: collapse; width: 100%;
    margin: 1.3em 0; font-size: .93em;
    display: block; overflow-x: auto;
  }}
  th, td {{ border: 1px solid #e2e2e2; padding: 7px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #fafafa; font-weight: 600; white-space: nowrap; }}
  strong {{ font-weight: 600; }}
  hr {{ border: 0; border-top: 1px solid #e8e8e8; margin: 2.4em 0; }}
  a {{ color: #1a5fb4; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ background: #f5f5f5; padding: .1em .35em; border-radius: 3px; font-size: .9em; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""

def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding='utf-8').read()
    body = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'sane_lists'],
        output_format='html5',
    )
    m = re.search(r'^#\s+(.+)$', text, re.M)
    title = m.group(1).strip() if m else os.path.basename(src)
    open(dst, 'w', encoding='utf-8').write(TPL.format(title=title, body=body))
    print(f"{src} -> {dst}")

if __name__ == '__main__':
    main()
