
from bs4 import BeautifulSoup
from pathlib import Path


def extract_javascript(file_path):

    file_path = Path(file_path)
    html = file_path.read_text(
        encoding="utf-8",
        errors="replace"
    )

    soup = BeautifulSoup(html, "html.parser")

    scripts = []
    inline_events = []
    external_scripts = []
    forms = []

    # -----------------------------------------------------
    # 1. EXTRACT SCRIPT TAGS
    # -----------------------------------------------------

    for script in soup.find_all("script"):

        if script.get("src"):

            external_scripts.append({
                "line": script.sourceline,
                "src": script.get("src")
            })

            continue

        code = script.string or script.get_text()

        if code and code.strip():

            position = html.find(code)

            start_line = (
                html[:position].count("\n") + 1
                if position >= 0
                else script.sourceline
            )

            scripts.append({
                "line": start_line,
                "code": code
            })

    # -----------------------------------------------------
    # 2. EXTRACT INLINE HTML EVENT HANDLERS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # 3. EXTRACT HTML FORMS
    # -----------------------------------------------------

    for form in soup.find_all("form"):

        fields = []

        for field in form.find_all(
            ["input", "select", "textarea", "button"]
        ):

            field_name = field.get("name")

            if field_name:

                fields.append({
                    "name": field_name,
                    "type": field.get("type", field.name)
                })

        forms.append({
            "id": form.get("id", "No ID"),
            "action": form.get("action", ""),
            "method": form.get("method", "GET").upper(),
            "line": form.sourceline,
            "fields": fields
        })

    return {
        "scripts": scripts,
        "inline_events": inline_events,
        "external_scripts": external_scripts,
        "forms": forms
    }
