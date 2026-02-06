"""
Split a MediaWiki XML export into individual article files.

Usage:
    python split_wiki.py [input_xml] [output_dir]

Defaults:
    input_xml  = Dwarf+Fortress+Wiki-20260206192244.xml (in script directory)
    output_dir = wiki (in script directory)

Each <page> becomes a separate file under output_dir.
Filename is derived from the <title> with unsafe characters replaced.
Only the latest revision's <text> content is saved.
"""

import os
import re
import sys
import xml.sax
import xml.sax.handler


def sanitize_filename(title: str) -> str:
    """Convert a wiki page title to a safe filename."""
    # Replace characters not allowed in Windows filenames
    name = re.sub(r'[<>:"/\\|?*]', "", title)
    # Replace whitespace runs with underscore
    name = re.sub(r"\s+", "", name)
    # Trim dots/spaces from ends (Windows restriction)
    name = name.strip(". ")
    # Limit length (leave room for .txt extension)
    if len(name) > 200:
        name = name[:200]
    return name


class WikiPageHandler(xml.sax.handler.ContentHandler):
    """SAX handler that streams through MediaWiki XML and writes each page to a file."""

    NAMESPACE = "http://www.mediawiki.org/xml/export-0.11/"

    def __init__(self, output_dir: str):
        super().__init__()
        self.output_dir = output_dir
        self.page_count = 0
        self.skip_count = 0

        # State tracking
        self._in_page = False
        self._in_title = False
        self._in_text = False
        self._in_ns = False
        self._title = ""
        self._ns = ""
        self._text = ""

    def startElementNS(self, name, qname, attrs):
        uri, localname = name
        if uri != self.NAMESPACE:
            return

        if localname == "page":
            self._in_page = True
            self._title = ""
            self._ns = ""
            self._text = ""
        elif localname == "title" and self._in_page:
            self._in_title = True
            self._title = ""
        elif localname == "ns" and self._in_page:
            self._in_ns = True
            self._ns = ""
        elif localname == "text" and self._in_page:
            self._in_text = True
            self._text = ""

    def endElementNS(self, name, qname):
        uri, localname = name
        if uri != self.NAMESPACE:
            return

        if localname == "title":
            self._in_title = False
        elif localname == "ns":
            self._in_ns = False
        elif localname == "text":
            self._in_text = False
        elif localname == "page":
            self._in_page = False
            self._write_page()

    def characters(self, content):
        if self._in_title:
            self._title += content
        elif self._in_ns:
            self._ns += content
        elif self._in_text:
            self._text += content

    def _write_page(self):
        title = self._title.strip()
        if not title:
            self.skip_count += 1
            return

        safe_name = sanitize_filename(title)
        if not safe_name:
            self.skip_count += 1
            return

        # Use namespace subdirectory for non-main namespace pages
        ns = self._ns.strip()
        if ns and ns != "0":
            subdir = os.path.join(self.output_dir, f"ns{ns}")
        else:
            subdir = self.output_dir

        os.makedirs(subdir, exist_ok=True)

        filepath = os.path.join(subdir, safe_name + ".txt")

        # Handle duplicate titles by appending a counter
        if os.path.exists(filepath):
            base = os.path.join(subdir, safe_name)
            counter = 2
            while os.path.exists(filepath):
                filepath = f"{base}{counter}.txt"
                counter += 1

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self._text)

        self.page_count += 1
        if self.page_count % 500 == 0:
            print(f"  ... {self.page_count} pages written")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    input_xml = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.path.join(script_dir, "Dwarf+Fortress+Wiki-20260206192244.xml")
    )
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(script_dir, "wiki")

    if not os.path.isfile(input_xml):
        print(f"Error: input file not found: {input_xml}")
        sys.exit(1)

    print(f"Input:  {input_xml}")
    print(f"Output: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    handler = WikiPageHandler(output_dir)
    parser = xml.sax.make_parser()
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    parser.setContentHandler(handler)

    print("Parsing...")
    parser.parse(input_xml)

    print(f"\nDone! {handler.page_count} pages written, {handler.skip_count} skipped.")


if __name__ == "__main__":
    main()
