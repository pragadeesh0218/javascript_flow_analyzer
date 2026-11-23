
import re


def analyze_javascript(code, start_line=1):

    results = []

    lines = code.splitlines()

    for index, line in enumerate(lines):

        current_line = start_line + index
        statement = line.strip()

        if not statement or statement.startswith("//"):
            continue

        explanation = None

        # 1. Event listeners
        if re.search(r'\.on\s*\(\s*["\'](\w+)["\']', statement):
            match = re.search(
                r'\.on\s*\(\s*["\'](\w+)["\']',
                statement
            )
            event = match.group(1)
            explanation = f"Registers a {event} event handler."

        elif re.search(r'\.addEventListener\s*\(', statement):
            match = re.search(
                r'\.addEventListener\s*\(\s*["\'](\w+)["\']',
                statement
            )
            if match:
                explanation = (
                    f"Registers a {match.group(1)} event listener."
                )

        # 2. Function declarations
        elif re.search(r'\bfunction\s+(\w+)\s*\(', statement):
            match = re.search(
                r'\bfunction\s+(\w+)\s*\(',
                statement
            )
            explanation = f"Defines the function {match.group(1)}."

        # 3. Conditional statements
        elif re.match(r'^\s*if\s*\(', statement):
            explanation = "Checks a condition before executing code."

        elif re.match(r'^\s*else\s+if\s*\(', statement):
            explanation = "Checks another condition if the previous condition was false."

        elif re.match(r'^\s*else\b', statement):
            explanation = "Executes the alternative branch."

        # 4. UI changes
        elif re.search(r'\.hide\s*\(', statement):
            explanation = "Hides the selected HTML element."

        elif re.search(r'\.show\s*\(', statement):
            explanation = "Displays the selected HTML element."

        elif re.search(r'\.val\s*\(', statement):
            explanation = "Gets or changes the value of an input or selected element."

        elif re.search(r'\.prop\s*\(', statement):
            explanation = "Changes or reads an HTML element property."

        elif re.search(r'\.attr\s*\(', statement):
            explanation = "Gets or changes an HTML attribute."

        # 5. Form submission
        elif re.search(r'\.submit\s*\(', statement):
            explanation = "Submits the selected form."

        # 6. AJAX / API calls
        elif re.search(r'\$\.ajax\s*\(', statement):
            explanation = "Starts an AJAX request to communicate with a server."

        elif re.search(r'\bfetch\s*\(', statement):
            explanation = "Starts an HTTP request using fetch()."

        elif re.search(r'\.post\s*\(', statement):
            explanation = "Sends an HTTP POST request."

        elif re.search(r'\.get\s*\(', statement):
            explanation = "Sends an HTTP GET request."

        # 7. Page navigation
        elif re.search(r'window\.location|location\.href', statement):
            explanation = "Changes the browser's current page or URL."

        # 8. Function calls
        elif re.search(r'^\$?\w+\s*\([^)]*\)\s*;?$', statement):
            match = re.match(
                r'^\$?(\w+)\s*\(',
                statement
            )
            if match:
                name = match.group(1)
                if name not in ("if", "for", "while", "switch"):
                    explanation = f"Calls the function {name}()."

        if explanation:
            results.append({
                "line": current_line,
                "code": statement,
                "explanation": explanation
            })

    return results
