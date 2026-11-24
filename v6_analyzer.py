
import re


# =========================================================
# 1. ANALYZE ACTIONS INSIDE EVENT HANDLERS
# =========================================================

def analyze_event_actions(code):

    results = []

    # Prevent default browser behavior
    if re.search(
        r'\bevent\s*\.\s*preventDefault\s*\(',
        code
    ):

        results.append(
            "Calls event.preventDefault(). "
            "Stops the browser's default event behavior."
        )

    # Form submit
    if re.search(
        r'\.submit\s*\(',
        code
    ):

        results.append(
            "Calls submit() to submit an HTML form."
        )

    # Form requestSubmit
    if re.search(
        r'\.requestSubmit\s*\(',
        code
    ):

        results.append(
            "Calls requestSubmit() to trigger form submission."
        )

    # Browser navigation
    navigation_patterns = [
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*href\s*=',
            "Changes the browser URL using location.href."
        ),
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*assign\s*\(',
            "Navigates to another URL using location.assign()."
        ),
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*replace\s*\(',
            "Navigates using location.replace(), replacing the current history entry."
        )
    ]

    for pattern, description in navigation_patterns:

        if re.search(pattern, code):

            results.append(description)

    return results


# =========================================================
# 2. EXTRACT NAVIGATION TARGETS
# =========================================================

def analyze_navigation(code, start_line=1):

    results = []

    patterns = [
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*href\s*=\s*'
            r'(["\'])(.*?)\1',
            "location.href"
        ),
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*assign\s*'
            r'\(\s*(["\'])(.*?)\1',
            "location.assign()"
        ),
        (
            r'\b(?:window\s*\.\s*)?location\s*\.\s*replace\s*'
            r'\(\s*(["\'])(.*?)\1',
            "location.replace()"
        )
    ]

    for index, line in enumerate(code.splitlines()):

        statement = line.strip()

        if not statement or statement.startswith("//"):
            continue

        for pattern, navigation_type in patterns:

            match = re.search(pattern, statement)

            if match:

                results.append({
                    "line": start_line + index,
                    "type": navigation_type,
                    "target": match.group(2),
                    "code": statement
                })

                break

    return results
