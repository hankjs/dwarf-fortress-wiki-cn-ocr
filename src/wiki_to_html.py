"""
Wiki 格式转 HTML 模块
将 MediaWiki 格式内容转换为 HTML，支持链接、图片、表格、Markdown 语法等
"""

import hashlib
import html
import re
from urllib.parse import quote


def wiki_to_html(content):
    """
    将wiki格式内容转为HTML，[[link]] 变为可点击链接，[[File:...]] 变为图片
    
    Args:
        content: MediaWiki 格式的文本内容
        
    Returns:
        tuple: (html_content, url_to_filename_dict)
            - html_content: 转换后的 HTML 字符串
            - url_to_filename_dict: URL 到文件名的映射，用于 404 后解析真实 URL
    """
    # 存储 URL 到文件名的映射，用于 404 后解析真实 URL
    url_to_filename = {}

    # 先提取 [[File:...]] 替换为占位符（避免被 html.escape 和后续正则干扰）
    file_placeholders = {}

    def replace_file(m):
        parts = m.group(1).split("|")
        filename = parts[0].replace(" ", "_")
        # MediaWiki 首字母大写
        if filename:
            filename = filename[0].upper() + filename[1:]
        # 解析宽度参数
        width = ""
        for p in parts[1:]:
            p = p.strip()
            if p.endswith("px") and p[:-2].isdigit():
                width = p[:-2]
        # 基于MD5哈希构造真实图片URL
        h = hashlib.md5(filename.encode()).hexdigest()
        base = f"https://dwarffortresswiki.org/images"
        # 始终使用原始图片URL，用HTML width属性控制显示大小
        # (缩略图路径/thumb/对某些图片不存在，会返回404)
        # 对文件名进行URL编码，处理空格等特殊字符
        encoded_filename = quote(filename)
        img_url = f"{base}/{h[0]}/{h[:2]}/{encoded_filename}"
        w_attr = f' width="{width}"' if width else ""
        placeholder = f"__FILE_PLACEHOLDER_{len(file_placeholders)}__"
        file_placeholders[placeholder] = f'<br><img src="{img_url}"{w_attr}><br>'
        # 保存映射关系
        url_to_filename[img_url] = filename
        # 调试日志
        print(f"[DEBUG] Wiki图片: filename={filename}")
        print(f"[DEBUG] Wiki图片: img_url={img_url}")
        return placeholder

    content = re.sub(
        r"\[\[File:([^\]]+)\]\]", replace_file, content, flags=re.IGNORECASE
    )

    # 提取并保护已有的 HTML 标签（如 <span style="color:green">）
    html_placeholders = {}
    html_id = 0

    def protect_html(m):
        nonlocal html_id
        placeholder = f"__HTML_TAG_{html_id}__"
        html_id += 1
        html_placeholders[placeholder] = m.group(0)
        return placeholder

    # 匹配 HTML 标签：<tag> 或 <tag attr="value"> 或 </tag>
    content = re.sub(r"</?[a-zA-Z][^>]*>", protect_html, content)

    # 先对普通文本内容进行HTML转义
    content = html.escape(content)

    # 还原已有的 HTML 标签
    for placeholder, html_tag in html_placeholders.items():
        content = content.replace(placeholder, html_tag)

    # 还原图片占位符（图片HTML已经安全，不需要再次转义）
    for placeholder, img_html in file_placeholders.items():
        content = content.replace(placeholder, img_html)

    # [http://... 显示文本] 或 [http://...] 外部链接格式
    # 先提取外部链接，保护起来
    external_link_placeholders = {}
    el_id = 0

    def replace_external_link(m):
        nonlocal el_id
        url = m.group(1)
        text = m.group(2) if m.group(2) else url
        placeholder = f"__EXT_LINK_{el_id}__"
        el_id += 1
        external_link_placeholders[placeholder] = (
            f'<a href="{url}" target="_blank" style="color:#1a73e8;text-decoration:none;">{text}</a>'
        )
        return placeholder

    # 匹配 [http://...] 或 [http://... 显示文本]
    content = re.sub(
        r"\[(https?://[^\s\]]+)(?:\s+([^\]]+))?\]",
        replace_external_link,
        content,
    )

    # [[link|display]] 格式 (MediaWiki标准格式：[[目标|显示文本]])
    content = re.sub(
        r"\[\[([^\]|]+)\|([^\]]+)\]\]",
        r'<a href="wiki:\1" style="color:#1a73e8;text-decoration:none;">\2</a>',
        content,
    )
    # [[link]] 格式
    content = re.sub(
        r"\[\[([^\]]+)\]\]",
        r'<a href="wiki:\1" style="color:#1a73e8;text-decoration:none;">\1</a>',
        content,
    )
    # '''bold''' 格式
    content = re.sub(
        r"&#x27;&#x27;&#x27;(.+?)&#x27;&#x27;&#x27;", r"<b>\1</b>", content
    )
    # 还原外部链接占位符
    for placeholder, link_html in external_link_placeholders.items():
        content = content.replace(placeholder, link_html)

    # ========== Markdown 语法增强处理（在 wiki 处理后） ==========
    # 注意：html.escape() 默认不会转义反引号 `，所以直接匹配原始字符

    # 1. 代码块 ```code```
    def replace_code_block(m):
        code = m.group(1)
        code = code.replace("<br>", "\n")
        return f"<pre style='background:#f4f4f4;padding:8px;border-radius:4px;overflow-x:auto;'><code>{code}</code></pre>"

    content = re.sub(r"```(.*?)```", replace_code_block, content, flags=re.DOTALL)

    # 2. 行内代码 `code`
    content = re.sub(
        r"`([^`]+)`",
        r"<code style='background:#f4f4f4;padding:2px 4px;border-radius:3px;font-family:monospace;'>\1</code>",
        content,
    )

    # 3. 特殊语法 ==text== → 带高亮的 h2（在斜体之前处理）
    content = re.sub(
        r"==(.+?)==",
        r'<h2 style="background-color:#ffffcc;padding:8px 12px;border-left:4px solid #ffcc00;margin:12px 0;">\1</h2>',
        content,
    )
    # 修复：要求 =text= 前后是空白或边界，避免匹配 HTML 属性中的 =
    content = re.sub(
        r"(?<!\S)=(.+?)=(?!\S)",
        r'<h3 style="background-color:#ffffcc;padding:8px 12px;border-left:4px solid #ffcc00;margin:12px 0;">\1</h3>',
        content,
    )

    # 4. 保护已有的 HTML 标签（如 <span style="color:green">）
    html_tag_pattern = re.compile(r"<[^>]+>")
    protected_html = {}
    ph_id = 0

    def protect_html_tag(m):
        nonlocal ph_id
        key = f"@@HTMLTAG{ph_id}@@"
        ph_id += 1
        protected_html[key] = m.group(0)
        return key

    content = html_tag_pattern.sub(protect_html_tag, content)

    # 5. MediaWiki 表格 {| ... |}（在斜体处理之前，避免 LAND_HOLDER 被处理）
    def process_table(match):
        table_content = match.group(1)

        # 处理 {{prettytable}} 模板
        table_attrs = ""
        if "{{prettytable}}" in table_content:
            table_attrs = ' class="prettytable anchortable" border="1" cellpadding="4" cellspacing="0" style="margin: 1em 1em 1em 0; background: #f9f9f9; border: 1px #aaa solid; border-collapse: collapse;"'
            # 移除模板标记
            table_content = table_content.replace("{{prettytable}}", "")

        html_rows = []
        current_row = None
        row_attrs = ""

        # 首先，将内容按行分割，但处理行内 |- 的情况
        # 先统一处理行内 |-
        # 例如：! LAND_HOLDER|-| civilization| ...
        # 应该变成：! LAND_HOLDER\n|-| civilization| ...
        table_content = re.sub(r"(^|!)([^\n|]+)\|-", r"\1\2\n|-", table_content)

        lines = table_content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()  # 保留前导空格，但去除尾部空格

            if not line.strip():
                i += 1
                continue

            if line.strip().startswith("{|"):
                # 提取表格属性（如果有）
                stripped = line.strip()
                attrs = stripped[2:].strip()
                if attrs and "{{" not in attrs:
                    table_attrs = f" {attrs}{table_attrs}"
                i += 1
                continue

            if line.strip().startswith("|}"):
                if current_row:
                    html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")
                    current_row = None
                i += 1
                continue

            if line.strip().startswith("|-"):
                if current_row:
                    html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")
                current_row = []
                # 处理 |- 后的属性或 |-| 后的单元格
                rest = line.strip()[2:].strip()
                if rest.startswith("|"):
                    # 这是 |-| 简化语法，后面紧跟单元格
                    rest = rest[1:].strip()  # 去掉第一个 |
                    # 按 | 或 || 分隔单元格
                    cells = re.split(r"\|\|?\s*", rest)
                    cells = [c.strip() for c in cells if c.strip()]
                    for cell in cells:
                        current_row.append(
                            f"<td>{cell}</td>"
                        )
                    row_attrs = ""
                else:
                    row_attrs = rest
                    # 反转义引号，因为 html.escape 已经执行过了
                    row_attrs = row_attrs.replace("&quot;", '"')
                    if row_attrs:
                        row_attrs = f" {row_attrs}"
                i += 1
                continue

            if line.strip().startswith("!"):
                if current_row is None:
                    current_row = []
                stripped = line.strip()
                cells = stripped[1:].split("!!")
                for cell in cells:
                    cell = cell.strip()
                    if "|" in cell and not cell.startswith("[["):
                        parts = cell.split("|", 1)
                        attrs = f" {parts[0].strip()}" if parts[0].strip() else ""
                        cell_content = parts[1].strip() if len(parts) > 1 else ""
                    else:
                        attrs = ""
                        cell_content = cell
                    current_row.append(f"<th{attrs}>{cell_content}</th>")
                i += 1
                continue

            if line.strip().startswith("|"):
                if current_row is None:
                    current_row = []
                    row_attrs = ""
                stripped = line.strip()
                cells = stripped[1:].split("||")
                for cell in cells:
                    cell = cell.strip()
                    current_row.append(f"<td>{cell}</td>")
                i += 1
                continue

            i += 1

        if current_row:
            html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")

        table_html = f"<table{table_attrs}><tbody>{''.join(html_rows)}</tbody></table>"
        return table_html

    content = re.sub(
        r"\{\|(.*?)\|\}",
        process_table,
        content,
        flags=re.DOTALL,
    )

    # 表格处理完后，再次保护新生成的 HTML 标签
    content = html_tag_pattern.sub(protect_html_tag, content)

    # 7. 粗体 **bold**（markdown 风格）- 优先于斜体处理
    content = re.sub(r"\*\*([^\*]+)\*\*", r"<b>\1</b>", content)

    # 8. 斜体 *italic* 或 _italic_
    content = re.sub(r"\*(?!\s)([^\*]+?)(?<!\s)\*", r"<i>\1</i>", content)
    # 斜体 _text_：要求前后不是字母数字，避免匹配 LAND_HOLDER 这样的变量名
    content = re.sub(
        r"(?<![a-zA-Z0-9])_(?!\s)([^_]+?)(?<!\s)_(?![a-zA-Z0-9])",
        r"<i>\1</i>",
        content,
    )

    # 还原保护的 HTML 标签
    for key, val in protected_html.items():
        content = content.replace(key, val)

    # 6. Markdown 链接 [text](url)
    content = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s\)]+)\)",
        r'<a href="\2" target="_blank" style="color:#1a73e8;text-decoration:none;">\1</a>',
        content,
    )

    # 7. 分隔线 --- 或 ***
    content = re.sub(
        r"^---+|<br>---|<hr>",
        "<hr style='border:none;border-top:1px solid #ddd;margin:16px 0;'>",
        content,
    )
    content = re.sub(
        r"^\*\*\*+|<br>\*\*\*",
        "<hr style='border:none;border-top:1px solid #ddd;margin:16px 0;'>",
        content,
    )

    # 8. 引用块 > quote (简单实现，单行的)
    # 注意：> 已经被 html.escape 转义成了 &gt;
    content = re.sub(
        r"^&gt;\s+(.+)$",
        r'<blockquote style="border-left:4px solid #ddd;margin:8px 0;padding:8px 16px;background:#f9f9f9;color:#666;">\1</blockquote>',
        content,
        flags=re.MULTILINE,
    )

    # 9. 无序列表 - item 或 * item (简单处理，不处理嵌套)
    # 收集列表项
    def process_ul(match):
        # 按 \\n 分割，因为此时还没有转成 <br>
        items = match.group(0).strip().split("\n")
        list_html = ["<ul style='margin:8px 0;padding-left:24px;'>"]
        for item in items:
            item = item.strip()
            if item.startswith("- ") or item.startswith("* "):
                item = item[2:]
                list_html.append(f"<li style='margin:4px 0;'>{item}</li>")
            elif item:
                list_html.append(f"<li style='margin:4px 0;'>{item}</li>")
        list_html.append("</ul>")
        return "".join(list_html)

    # 匹配连续的列表项（以 - 或 * 开头）
    content = re.sub(
        r"(?:^|\n)(?:[\t ]*[-\*][\t ]+.+\n?)+",
        process_ul,
        content,
        flags=re.MULTILINE,
    )

    # 10. 有序列表 1. item 或 # item (MediaWiki 格式)
    def process_ol(match):
        # 按 \\n 分割，因为此时还没有转成 <br>
        items = match.group(0).strip().split("\n")
        list_html = ["<ol style='margin:8px 0;padding-left:24px;'>"]
        for item in items:
            item = item.strip()
            if re.match(r"^\d+\.\s+", item):
                # 1. item 格式
                item = re.sub(r"^\d+\.\s+", "", item)
                list_html.append(f"<li style='margin:4px 0;'>{item}</li>")
            elif item.startswith("#"):
                # # item 格式 (MediaWiki)
                item = item[1:].strip()
                list_html.append(f"<li style='margin:4px 0;'>{item}</li>")
            elif item:
                list_html.append(f"<li style='margin:4px 0;'>{item}</li>")
        list_html.append("</ol>")
        return "".join(list_html)

    content = re.sub(
        r"(?:^|\n)(?:[\t ]*(?:\d+\.|#)[\t ]+.+\n?)+",
        process_ol,
        content,
        flags=re.MULTILINE,
    )

    # 11. MediaWiki 表格 {| ... |}
    # 表格处理需要在换行转换之前，因为表格包含多行
    def process_table2(match):
        table_content = match.group(1)

        # 解析表格属性（如 {{prettytable}}）
        table_attrs = ""
        if "{{prettytable}}" in table_content:
            table_attrs = (
                ' class="prettytable" style="border-collapse:collapse;width:100%;"'
            )

        html_rows = []
        current_row = None
        row_attrs = ""

        # 按行分割处理
        lines = table_content.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 跳过表格开始标记和模板
            if line.startswith("{|"):
                # 提取表格属性
                attrs = line[2:].strip()
                if attrs and "{{" not in attrs:
                    table_attrs = f" {attrs}"
                i += 1
                continue

            # 表格结束
            if line.startswith("|}"):
                if current_row:
                    html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")
                    current_row = None
                i += 1
                continue

            # 新行开始 |-
            if line.startswith("|-"):
                if current_row:
                    html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")
                current_row = []
                # 提取行属性
                row_attrs = line[2:].strip()
                if row_attrs:
                    row_attrs = f" {row_attrs}"
                else:
                    row_attrs = ""
                i += 1
                continue

            # 表头单元格 ! 或 !!
            if line.startswith("!"):
                # 自动开始新行（如果没有当前行）
                if current_row is None:
                    current_row = []
                    row_attrs = ' bgcolor="#ddd"'  # 默认表头行背景色
                # 处理 !! 分隔的多个表头
                cells = line[1:].split("!!")
                for cell in cells:
                    cell = cell.strip()
                    # 分离单元格内容和属性（如果有 | 分隔）
                    if "|" in cell and not cell.startswith("[["):
                        parts = cell.split("|", 1)
                        attrs = f" {parts[0].strip()}" if parts[0].strip() else ""
                        cell_content = parts[1].strip() if len(parts) > 1 else ""
                    else:
                        attrs = ""
                        cell_content = cell
                    current_row.append(
                        f"<th{attrs} style='border:1px solid #ddd;padding:8px;background:#f5f5f5;'>{cell_content}</th>"
                    )
                i += 1
                continue

            # 普通单元格 | 或 ||
            if line.startswith("|"):
                # 自动开始新行（如果没有当前行）
                if current_row is None:
                    current_row = []
                    row_attrs = ""
                # 处理 || 分隔的多个单元格
                cells = line[1:].split("||")
                for cell in cells:
                    cell = cell.strip()
                    # 处理单元格中的颜色标记（如 <span style="color:green">）
                    # 这些已经是 HTML，直接保留
                    current_row.append(
                        f"<td style='border:1px solid #ddd;padding:8px;'>{cell}</td>"
                    )
                i += 1
                continue

            i += 1

        # 结束最后一行
        if current_row:
            html_rows.append(f"<tr{row_attrs}>{''.join(current_row)}</tr>")

        table_html = f"<table{table_attrs}>{''.join(html_rows)}</table>"
        return table_html

    # 匹配 MediaWiki 表格（多行模式）
    content = re.sub(
        r"\{\|(.*?)\|\}",
        process_table2,
        content,
        flags=re.DOTALL,
    )

    # 保留换行
    content = content.replace("\n", "<br>")
    return content, url_to_filename
