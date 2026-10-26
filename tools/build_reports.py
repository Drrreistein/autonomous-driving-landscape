import os, re, glob, html
import markdown

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, 'reports/md')
OUT = os.path.join(REPO, 'reports')

TPL = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
:root{{--ink:#111820;--ink2:#2c3644;--sub:#5f6b7a;--line:#e4e7ec;--line2:#eef1f4;--red:#a8271f;--blue:#1b4a75;--bg:#ffffff;--paper:#fafaf8;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Hiragino Sans GB",-apple-system,BlinkMacSystemFont,"Helvetica Neue",sans-serif;font-size:15.5px;line-height:1.85;-webkit-font-smoothing:antialiased;}}
.bar{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);}}
.bar-in{{max-width:820px;margin:0 auto;padding:12px 24px;display:flex;justify-content:space-between;align-items:center;gap:16px;font-size:13px;}}
.bar a{{color:var(--blue);text-decoration:none;}}
.bar a:hover{{text-decoration:underline;}}
.bar .right{{color:var(--sub);font-size:12px;}}
.wrap{{max-width:820px;margin:0 auto;padding:40px 24px 90px;background:var(--bg);box-shadow:0 0 0 1px var(--line2);}}
h1{{font-size:30px;line-height:1.35;margin:0 0 22px;font-weight:650;letter-spacing:-.01em;}}
h2{{font-size:21px;margin:44px 0 14px;font-weight:650;padding-bottom:8px;border-bottom:1px solid var(--line);}}
h3{{font-size:17px;margin:30px 0 10px;font-weight:650;color:var(--ink2);}}
h4{{font-size:15px;margin:22px 0 8px;font-weight:650;color:var(--ink2);}}
p{{margin:0 0 1.05em;}}
strong{{font-weight:650;}}
em{{font-style:normal;background:linear-gradient(transparent 62%,rgba(168,39,31,.16) 62%);}}
a{{color:var(--blue);}}
blockquote{{margin:20px 0;padding:14px 20px;border-left:3px solid var(--blue);background:#f4f8fb;color:var(--ink2);font-size:14px;}}
blockquote p:last-child{{margin-bottom:0;}}
hr{{border:0;border-top:1px solid var(--line);margin:34px 0;}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:20px 0;}}
th{{text-align:left;font-weight:650;border-top:1.5px solid var(--ink);border-bottom:1px solid var(--ink);padding:9px 10px;background:#fcfcfb;}}
td{{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top;}}
tbody tr:hover td{{background:#fcfcfb;}}
td[style*="right"],th[style*="right"]{{font-family:"SF Mono",Menlo,monospace;}}
ul,ol{{margin:0 0 1.1em;padding-left:1.4em;}}
li{{margin-bottom:.4em;}}
code{{background:#f2f4f6;padding:1px 5px;border-radius:3px;font-size:.88em;font-family:"SF Mono",Menlo,monospace;}}
.toc{{border:1px solid var(--line);padding:16px 20px;margin:0 0 34px;background:#fcfcfb;font-size:13.5px;}}
.toc .t{{font-weight:650;margin-bottom:8px;font-size:12px;letter-spacing:.08em;color:var(--sub);}}
.toc a{{display:block;padding:3px 0;color:var(--ink2);text-decoration:none;border-bottom:1px dashed transparent;}}
.toc a:hover{{color:var(--red);border-bottom-color:var(--line);}}
.toc a.l3{{padding-left:18px;color:var(--sub);font-size:12.8px;}}
.foot{{margin-top:60px;padding-top:20px;border-top:1px solid var(--line);font-size:12px;color:var(--sub);}}
@media (max-width:720px){{.wrap{{padding:26px 16px 70px;}}h1{{font-size:24px;}}table{{font-size:12px;}}}}
@media print{{.bar,.toc{{display:none;}}.wrap{{box-shadow:none;max-width:none;}}}}
</style>
</head>
<body>
<div class="bar"><div class="bar-in">
  <a href="../index.html">← 返回产业链图谱</a>
  <span class="right">智驾产业全貌 · 公司调研</span>
</div></div>
<div class="wrap">
{body}
<div class="foot">本页由 Markdown 原稿自动生成，内容以原稿为准。数据与观点仅作研究记录，不构成投资建议。</div>
</div>
</body>
</html>
'''

def conv(path):
    raw = open(path, encoding='utf-8').read()
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists', 'nl2br'])
    body = md.convert(raw)
    # title
    m = re.search(r'<h1[^>]*>(.*?)</h1>', body, re.S)
    title = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else os.path.basename(path)
    if m:
        body = body[:m.start()] + body[m.end():]
    # toc from h2
    heads = re.findall(r'<h2[^>]*>(.*?)</h2>', body, re.S)
    if len(heads) >= 3:
        items = []
        for i, h in enumerate(heads):
            t = re.sub(r'<[^>]+>', '', h).strip()
            items.append(f'<a href="#h{i}">{t}</a>')
        # inject ids
        cnt = [0]
        def add_id(mm):
            s = f'<h2 id="h{cnt[0]}"'
            cnt[0] += 1
            return s
        body = re.sub(r'<h2', add_id, body)
        toc = '<div class="toc"><div class="t">目录</div>' + ''.join(items) + '</div>'
        body = toc + body
    body = '<h1>' + html.escape(title) + '</h1>' + body
    return title, body

n = 0
for p in sorted(glob.glob(os.path.join(SRC, '*.md'))):
    title, body = conv(p)
    out = os.path.join(OUT, os.path.splitext(os.path.basename(p))[0] + '.html')
    open(out, 'w', encoding='utf-8').write(TPL.format(title=html.escape(title), body=body))
    n += 1
print('converted', n)
