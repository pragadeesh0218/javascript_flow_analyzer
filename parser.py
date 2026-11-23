
from bs4 import BeautifulSoup
from pathlib import Path


def extract_javascript(file_path):
    file_path = Path(file_path)
    html = file_path.read_text(encoding="utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")

    scripts = []
    inline_events = []
    external_scripts = []

    # Extract script tags
    for script in soup.find_all("script"):

        if script.get("src"):
            external_scripts.append({
                "line": script.sourceline,
                "src": script.get("src")
            })
            continue

        code = script.string or script.get_text()

        if code and code.strip():
            # Find approximate starting line in original file
            position = html.find(code)
            start_line = (
                html[:position].count("\n") + 1
                if position >= 0 else script.sourceline
            )

            scripts.append({
                "line": start_line,
                "code": code
            })

    # Extract inline event handlers
    for tag in soup.find_all(True):

        for attr, value in tag.attrs.items():

            if attr.lower().startswith("on"):

                if isinstance(value, list):
                    value = " ".join(value)

                inline_events.append({
                    "line": tag.sourceline,
                    "element": tag.name,
                    "event": attr,
                    "code": value
                })

    return {
        "scripts": scripts,
        "inline_events": inline_events,
        "external_scripts": external_scripts
    }
