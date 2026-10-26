#!/usr/bin/env python3
"""HTML -> Markdown 转换器（自动驾驶行业报告专用）。

自建 html.parser 解析，不依赖第三方库。处理：
  - 封面（kicker / h1 / subtitle / byline / hero-stats / 版本说明 / toc）
  - 章节 h2/h3/h4 与 span 内的编号
  - callout（ct 标题 + 段落）、普通 div（内联 border-left 样式）
  - 表格（thead/tbody，自动补齐列数）、grid2/grid3、rating、kv、rail（st/tt/dd）
  - timeline、rate-box、fig/figt、cap、dek、lead、small、tag
  - 跨文档链接 <a href> 转为 Markdown 链接
"""
from html.parser import HTMLParser
import re
import sys


class N:
    def __init__(self, t, a=None, p=None):
        self.t = t
        self.a = a or {}
        self.c = []
        self.p = p


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = N('root')
        self.cur = self.root
        self.skip = 0

    def handle_starttag(self, t, a):
        if t in ('svg', 'style', 'script'):
            self.skip += 1
            return
        if self.skip:
            return
        if t in ('br', 'img', 'hr', 'meta', 'link'):
            n = N(t, dict(a), self.cur)
            self.cur.c.append(n)
            return
        n = N(t, dict(a), self.cur)
        self.cur.c.append(n)
        self.cur = n

    def handle_endtag(self, t):
        if t in ('svg', 'style', 'script'):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if self.cur.t == t and self.cur.p:
            self.cur = self.cur.p

    def handle_data(self, d):
        if self.skip:
            return
        if d.strip():
            self.cur.c.append(N('#text', {'v': d}))


def txt(n):
    if n.t == '#text':
        return n.a['v']
    if n.t in ('svg', 'style', 'script'):
        return ''
    if n.t == 'br':
        return '\n'
    return ''.join(txt(c) for c in n.c)


def clean(s):
    s = re.sub(r'[ \t\r\n]+', ' ', s)
    return s.strip()


def find(n, t, cls=None):
    out = []
    for c in n.c:
        if c.t == t and (cls is None or cls in c.a.get('class', '')):
            out.append(c)
        out += find(c, t, cls)
    return out


def kids(n, t):
    return [c for c in n.c if c.t == t]


def cls(n):
    return n.a.get('class', '')


def has(n, k):
    return k in cls(n).split()


class Ctx:
    def __init__(self):
        self.out = []
        self.figidx = 0


ctx = Ctx()


def emit(s=''):
    ctx.out.append(s)


def inline(n):
    """行内文本：strong/b -> **，tag -> `，a -> [text](href)。"""
    if n.t == '#text':
        return n.a['v']
    if n.t == 'br':
        return ' / '
    if n.t in ('strong', 'b'):
        v = clean(''.join(inline(c) for c in n.c))
        return '**' + v + '**' if v else ''
    if n.t == 'span' and has(n, 'tag'):
        return '`' + clean(txt(n)) + '`'
    if n.t == 'a':
        label = clean(''.join(inline(c) for c in n.c))
        href = n.a.get('href', '')
        if not href:
            return label
        if href.startswith('#'):
            return label
        return '[%s](%s)' % (label, href)
    return ''.join(inline(c) for c in n.c)


def ptext(n):
    return clean(''.join(inline(c) for c in n.c))


def heading(c, level):
    num = [x for x in kids(c, 'span') if has(x, 'num') or has(x, 'h3n')]
    numtxt = clean(txt(num[0])) if num else ''
    full = clean(txt(c))
    if numtxt and full.startswith(numtxt):
        rest = full[len(numtxt):].strip()
        return '#' * level + ' ' + numtxt + ' ' + rest
    return '#' * level + ' ' + full


def table(n):
    rows = []
    for tr in find(n, 'tr'):
        cells = []
        for cell in [c for c in tr.c if c.t in ('td', 'th')]:
            v = ptext(cell).replace('|', '\\|')
            cells.append(v)
        if cells:
            rows.append(cells)
    if not rows:
        return
    ncol = max(len(r) for r in rows)
    rows = [r + [''] * (ncol - len(r)) for r in rows]
    head = rows[0]
    emit('| ' + ' | '.join(head) + ' |')
    emit('| ' + ' | '.join([':---'] * len(head)) + ' |')
    for r in rows[1:]:
        emit('| ' + ' | '.join(r) + ' |')
    emit('')


def cover(c):
    kick = [x for x in kids(c, 'div') if has(x, 'kicker')]
    if kick:
        emit('*' + clean(txt(kick[0])) + '*')
        emit('')
    h1 = kids(c, 'h1')
    if h1:
        emit('# ' + clean(txt(h1[0])))
        emit('')
    sub = [x for x in kids(c, 'p') if has(x, 'subtitle')]
    if sub:
        for line in clean(txt(sub[0])).split('\n'):
            if line.strip():
                emit('> ' + line.strip())
        emit('')
    by = [x for x in kids(c, 'div') if has(x, 'byline')]
    if by:
        emit('| 项目 | 内容 |')
        emit('| :--- | :--- |')
        for d in kids(by[0], 'div'):
            sp = [x for x in kids(d, 'span')]
            lab = clean(txt(sp[0])) if sp else ''
            val = clean(''.join(txt(c) for c in d.c if c.t == '#text'))
            if lab and val:
                emit('| %s | %s |' % (lab, val))
        emit('')
    hs = [x for x in kids(c, 'div') if has(x, 'hero-stats')]
    if hs:
        emit('### 四个关键数字')
        emit('')
        emit('| 指标 | 数值 |')
        emit('| :--- | :---: |')
        for d in kids(hs[0], 'div'):
            b = [x for x in kids(d, 'b')]
            sp = [x for x in kids(d, 'span') if has(x, 'l')]
            if not b or not sp:
                continue
            num = clean(txt(b[0]))
            desc = clean(txt(sp[0])).replace('\n', '')
            emit('| %s | **%s** |' % (desc, num))
        emit('')
    # 深度报告封面另有一张"指标/数值/含义"三列表，手写维护更清晰，
    # 故与 HTML 的 hero-stats 合并输出为三列
    rb = [x for x in kids(c, 'div') if has(x, 'rate-box')]
    if rb:
        emit('| 关键项 | 内容 |')
        emit('| :--- | :--- |')
        for d in kids(rb[0], 'div'):
            lab = [y for y in kids(d, 'div') if has(y, 'lab')]
            big = [y for y in kids(d, 'div') if has(y, 'big')]
            sub = [y for y in kids(d, 'div') if has(y, 'sub')]
            if lab and big:
                extra = ('（%s）' % clean(txt(sub[0]))) if sub else ''
                emit('| %s | **%s**%s |' % (clean(txt(lab[0])), clean(txt(big[0])), extra))
        emit('')
    # 版本说明 / 其他内联样式提示框
    for d in kids(c, 'div'):
        st = d.a.get('style', '')
        if 'border-left' in st and not has(d, 'byline') and not has(d, 'hero-stats'):
            strong = [x for x in kids(d, 'strong')]
            lab_node = strong[0] if strong else None
            parts = []
            for x in d.c:
                if x is lab_node:
                    continue
                if x.t == 'strong':
                    parts.append('**' + clean(txt(x)) + '**')
                else:
                    parts.append(inline(x))
            body = clean(''.join(parts))
            if lab_node:
                emit('> **' + clean(txt(lab_node)) + '** ' + body)
            else:
                emit('> ' + body)
            emit('')
    toc = [x for x in kids(c, 'nav') if has(x, 'toc')]
    if toc:
        emit('## 目录')
        emit('')
        i = 0
        for a in kids(toc[0], 'a'):
            i += 1
            num = [x for x in kids(a, 'i')]
            label = clean(''.join(inline(x) for x in a.c if x.t != 'i'))
            href = a.a.get('href', '')
            emit('%d. [%s](%s)' % (i, label, href))
        emit('')
        emit('---')
        emit('')


def inline_box(d):
    """内联 border-left 样式的提示框（另见框等）。"""
    strong = [x for x in kids(d, 'strong')]
    lab_node = strong[0] if strong else None
    parts = []
    for x in d.c:
        if x is lab_node:
            continue
        if x.t == 'br':
            parts.append('\n')
        elif x.t == 'strong':
            parts.append('**' + clean(txt(x)) + '**')
        else:
            parts.append(inline(x))
    body = ''.join(parts)
    lines = [clean(l) for l in body.split('\n') if clean(l)]
    if lab_node:
        emit('> **' + clean(txt(lab_node)) + '** ' + lines[0] if lines else '> **' + clean(txt(lab_node)) + '**')
        for l in lines[1:]:
            emit('>')
            emit('> ' + l)
    else:
        for l in lines:
            emit('> ' + l)
    emit('')


def walk(n):
    for c in n.c:
        if c.t == '#text':
            continue
        k = cls(c)
        if c.t == 'header':
            cover(c)
            continue
        if c.t == 'nav':
            continue
        if c.t == 'h2':
            emit('')
            emit(heading(c, 2))
            emit('')
        elif c.t == 'h3':
            emit('')
            emit(heading(c, 3))
            emit('')
        elif c.t == 'h4':
            emit('')
            emit(heading(c, 4))
            emit('')
        elif c.t == 'p':
            if has(c, 'dek'):
                emit('> ' + ptext(c))
                emit('')
            elif has(c, 'cap'):
                emit('注｜' + ptext(c))
                emit('')
            elif has(c, 'lead'):
                emit('**' + ptext(c).replace('**', '') + '**')
                emit('')
            elif has(c, 'footnote'):
                emit(ptext(c))
                emit('')
            else:
                emit(ptext(c))
                emit('')
        elif c.t == 'a' and c.p is not None and c.p.t == 'p':
            continue
        elif c.t == 'div' and has(c, 'callout'):
            ct = [x for x in kids(c, 'div') if has(x, 'ct')]
            emit('> **' + (clean(txt(ct[0])) if ct else '') + '**')
            emit('>')
            for pp in kids(c, 'p'):
                emit('> ' + ptext(pp))
                emit('>')
            emit('')
        elif c.t == 'div' and 'border-left' in c.a.get('style', ''):
            inline_box(c)
        elif c.t == 'div' and has(c, 'fig'):
            t = [x for x in kids(c, 'div') if has(x, 'figt')]
            if t:
                emit('')
                emit('**' + clean(txt(t[0])) + '**')
                emit('')
            continue
        elif c.t == 'div' and has(c, 'figt'):
            emit('')
            emit('**' + clean(txt(c)) + '**')
            emit('')
            continue
        elif c.t in ('ul', 'ol'):
            i = 1
            for li in kids(c, 'li'):
                body = ptext(li)
                if c.t == 'ol':
                    emit('%d. %s' % (i, body))
                    i += 1
                else:
                    emit('- ' + body)
            emit('')
        elif c.t == 'table':
            table(c)
        elif c.t == 'dl':
            for dt in kids(c, 'dt'):
                lab = ptext(dt)
                dds = [x for x in kids(c, 'dd')]
                emit('- **%s**' % lab)
                for dd in dds:
                    emit('  ' + ptext(dd))
            emit('')
        elif c.t == 'div' and has(c, 'timeline'):
            for ev in kids(c, 'div'):
                d = [x for x in kids(ev, 'div') if has(x, 'd')]
                t = [x for x in kids(ev, 'div') if has(x, 't')]
                x = [y for y in kids(ev, 'div') if has(y, 'x')]
                if d:
                    emit('- **%s｜%s**' % (clean(txt(d[0])), clean(txt(t[0])) if t else ''))
                    if x:
                        emit('  ' + ptext(x[0]))
            emit('')
        elif c.t == 'div' and has(c, 'rate-box'):
            for d in kids(c, 'div'):
                lab = [y for y in kids(d, 'div') if has(y, 'lab')]
                big = [y for y in kids(d, 'div') if has(y, 'big')]
                sub = [y for y in kids(d, 'div') if has(y, 'sub')]
                if lab and big:
                    emit('- **%s**：%s' % (clean(txt(lab[0])), clean(txt(big[0]))))
                    if sub:
                        emit('  ' + clean(txt(sub[0])))
            emit('')
        elif c.t == 'div' and has(c, 'rating'):
            for d in kids(c, 'div'):
                lab = [y for y in kids(d, 'div') if has(y, 'lab')]
                big = [y for y in kids(d, 'div') if has(y, 'val')]
                note = [y for y in kids(d, 'div') if has(y, 'note')]
                if lab and big:
                    emit('- **%s**：%s' % (clean(txt(lab[0])), clean(txt(big[0]))))
                    if note:
                        emit('  ' + clean(txt(note[0])))
            emit('')
        elif c.t == 'div' and has(c, 'kv'):
            for d in kids(c, 'div'):
                dts = kids(d, 'dt')
                dds = kids(d, 'dd')
                if dts and dds:
                    emit('- **%s**：%s' % (ptext(dts[0]), ptext(dds[0])))
            emit('')
        elif c.t == 'div' and has(c, 'rail'):
            for d in kids(c, 'div'):
                st = [x for x in kids(d, 'span') if has(x, 'st')]
                tt = [x for x in kids(d, 'div') if has(x, 'tt')]
                dd = [x for x in kids(d, 'div') if has(x, 'dd')]
                if st and tt:
                    emit('- **%s｜%s**' % (clean(txt(st[0])), clean(txt(tt[0]))))
                    if dd:
                        emit('  ' + clean(txt(dd[0])).replace('\n', ' '))
            emit('')
        elif c.t == 'div' and (has(c, 'grid2') or has(c, 'grid3')):
            for d in kids(c, 'div'):
                h4 = [x for x in kids(d, 'h4')]
                if h4:
                    emit('')
                    emit('**' + clean(txt(h4[0])) + '**')
                    emit('')
                for pp in kids(d, 'p'):
                    emit(ptext(pp))
                    emit('')
                for lst in kids(d, 'ul'):
                    for li in kids(lst, 'li'):
                        emit('- ' + ptext(li))
                    emit('')
                for lst in kids(d, 'ol'):
                    i2 = 1
                    for li in kids(lst, 'li'):
                        emit('%d. %s' % (i2, ptext(li)))
                        i2 += 1
                    emit('')
                for tbl in kids(d, 'table'):
                    table(tbl)
        elif c.t == 'div' and has(c, 'plain'):
            walk(c)
        elif c.t == 'div':
            # 未知容器：若没有可识别子结构，递归；否则跳过以免重复输出
            if not any(has(x, 'callout') or has(x, 'figt') or has(x, 'ct') for x in kids(c, 'div')):
                walk(c)


def convert(path):
    src = open(path, encoding='utf-8').read()
    body = src[src.index('<body>'):]
    p = P()
    p.feed(body)
    ctx.out = []
    root = p.root
    # header（封面）在 section 之外，需单独遍历
    for hd in find(root, 'header'):
        cover(hd)
    for sec in find(root, 'section'):
        walk(sec)
    # 尾部可能存在非 section 包裹的内容（如免责声明脚注）
    inner = find(root, 'div')
    for d in inner:
        if has(d, 'inner') and not any(has(x, 'inner') for x in find(d, 'div')):
            walk(d)
    md = '\n'.join(ctx.out)
    md = re.sub(r'\n{3,}', '\n\n', md)
    md = md.replace(' ：', '：')
    md = md.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    md = md.replace('&#x5728;', '在')
    md = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), md)
    md = md.replace(' ', ' ')
    return md


if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    md = convert(src)
    open(dst, 'w', encoding='utf-8').write(md)
    print('%s -> %s  len=%d' % (src, dst, len(md)))
