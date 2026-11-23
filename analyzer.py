
import re


# JavaScript keywords that should not be treated as function calls
IGNORED_CALLS = {
    # JavaScript keywords
    "if", "else", "for", "while", "switch",
    "catch", "function", "return", "typeof",
    "new", "throw", "try", "do", "await",
    "delete", "void",

    # Browser and JavaScript built-ins
    "alert", "confirm", "prompt",
    "parseInt", "parseFloat",
    "setTimeout", "setInterval",
    "clearTimeout", "clearInterval",

    # Console methods
    "log", "error", "warn", "info",

    # jQuery selector
    "$", "jQuery"
}


def find_matching_brace(code, open_pos):
    """
    Find the closing brace corresponding to an opening brace.
    Handles basic strings and comments.
    """

    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False

    i = open_pos

    while i < len(code):

        char = code[i]
        next_char = code[i + 1] if i + 1 < len(code) else ""

        if line_comment:
            if char == "\n":
                line_comment = False

        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                i += 1

        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None

        elif char == "/" and next_char == "/":
            line_comment = True
            i += 1

        elif char == "/" and next_char == "*":
            block_comment = True
            i += 1

        elif char in ("'", '"', "`"):
            quote = char

        elif char == "{":
            depth += 1

        elif char == "}":
            depth -= 1

            if depth == 0:
                return i

        i += 1

    return None


def extract_functions(code, start_line=1):

    functions = []

    pattern = re.compile(
        r'\bfunction\s+([A-Za-z_$][\w$]*)\s*'
        r'\(([^)]*)\)\s*\{'
    )

    for match in pattern.finditer(code):

        name = match.group(1)
        parameters = match.group(2)

        open_pos = match.end() - 1
        close_pos = find_matching_brace(code, open_pos)

        if close_pos is None:
            continue

        body = code[open_pos + 1:close_pos]

        line = start_line + code[:match.start()].count("\n")

        functions.append({
            "name": name,
            "parameters": parameters,
            "line": line,
            "body": body
        })

    return functions



def extract_function_calls(code):

    calls = []

    pattern = re.compile(
        r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\('
    )

    for match in pattern.finditer(code):

        name = match.group(1)

        if name in IGNORED_CALLS:
            continue

        # Ignore function declarations
        prefix = code[:match.start()].rstrip()

        if re.search(r'\bfunction\s*$', prefix):
            continue

        # Ignore object methods such as console.log()
        if match.start() > 0 and code[match.start() - 1] == ".":
            continue

        calls.append({
            "name": name,
            "position": match.start()
        })

    # Remove duplicates while preserving order
    unique_calls = []
    seen = set()

    for call in calls:

        if call["name"] not in seen:
            unique_calls.append(call)
            seen.add(call["name"])

    return unique_calls


def extract_event_handlers(code, start_line=1):

    events = []

    patterns = [
        (
            r'\.on\s*\(\s*["\'](\w+)["\']\s*,\s*'
            r'function\s*\([^)]*\)\s*\{',
            "jQuery"
        ),
        (
            r'\.addEventListener\s*\(\s*["\'](\w+)["\']'
            r'\s*,\s*function\s*\([^)]*\)\s*\{',
            "DOM"
        )
    ]

    for pattern, event_type in patterns:

        for match in re.finditer(pattern, code):

            event_name = match.group(1)

            open_pos = match.end() - 1
            close_pos = find_matching_brace(code, open_pos)

            if close_pos is None:
                continue

            body = code[open_pos + 1:close_pos]

            line = (
                start_line +
                code[:match.start()].count("\n")
            )

            # Find the selector for jQuery events
            selector = "Unknown element"

            if event_type == "jQuery":

                before = code[:match.start()]

                selector_match = re.search(
                    r'(\$\s*\(\s*["\'][^"\']+["\']\s*\))\s*$',
                    before
                )

                if selector_match:
                    selector = selector_match.group(1)

            events.append({
                "event": event_name,
                "type": event_type,
                "selector": selector,
                "line": line,
                "body": body
            })

    return events


def build_call_graph(functions):

    graph = {}

    for function in functions:

        calls = extract_function_calls(function["body"])

        graph[function["name"]] = calls

    return graph



def trace_function(name, function_map, graph, visited=None, depth=0):

    if visited is None:
        visited = set()

    if name in visited:
        return [{
            "depth": depth,
            "message": f"{name}() already visited. Possible recursion."
        }]

    if name not in function_map:
        return [{
            "depth": depth,
            "message": f"{name}() definition not found in this file."
        }]

    visited = visited | {name}

    function = function_map[name]

    results = [{
        "depth": depth,
        "message": (
            f"Function {name}() defined at line "
            f"{function['line']}."
        )
    }]

    body = function["body"]
    lines = body.splitlines()

    for index, line in enumerate(lines):

        statement = line.strip()

        if not statement or statement.startswith("//"):
            continue

        # Console output
        if re.search(r'console\.log\s*\(', statement):
            results.append({
                "depth": depth + 1,
                "message": "Displays a message in the browser console."
            })

        # Conditions
        elif re.match(r'if\s*\(', statement):
            results.append({
                "depth": depth + 1,
                "message": "Checks a condition."
            })

        # UI selection
        elif re.search(r'\$\s*\(', statement):
            results.append({
                "depth": depth + 1,
                "message": "Selects an HTML element using jQuery."
            })

        # Form submission
        if re.search(r'\.submit\s*\(', statement):
            results.append({
                "depth": depth + 1,
                "message": "Submits the selected HTML form."
            })

        # jQuery selector
        elif re.search(r'\$\s*\(', statement):
            results.append({
                "depth": depth + 1,
                "message": "Selects an HTML element using jQuery."
            })

        # Other function calls
        calls = extract_function_calls(statement)

        for call in calls:

            called_name = call["name"]

            results.append({
                "depth": depth + 1,
                "message": f"Calls {called_name}()."
            })

            if called_name in function_map:

                nested = trace_function(
                    called_name,
                    function_map,
                    graph,
                    visited,
                    depth + 2
                )

                results.extend(nested)

            else:

                results.append({
                    "depth": depth + 2,
                    "message": (
                        f"{called_name}() definition not found "
                        "in this file."
                    )
                })

    return results



def analyze_javascript(code, start_line=1):

    results = []

    lines = code.splitlines()

    for index, line in enumerate(lines):

        current_line = start_line + index
        statement = line.strip()

        if not statement or statement.startswith("//"):
            continue

        explanation = None

        if re.search(r'\.on\s*\(\s*["\'](\w+)["\']', statement):
            match = re.search(
                r'\.on\s*\(\s*["\'](\w+)["\']',
                statement
            )
            explanation = f"Registers a {match.group(1)} event handler."

        elif re.match(r'^\s*function\s+\w+', statement):
            match = re.search(r'function\s+(\w+)', statement)
            explanation = f"Defines the function {match.group(1)}."

        elif re.match(r'^\s*if\s*\(', statement):
            explanation = "Checks a condition."

        elif re.match(r'^\s*else\b', statement):
            explanation = "Executes an alternative branch."

        elif re.search(r'\$\s*\(', statement):
            explanation = "Selects an HTML element using a jQuery selector."

        elif re.search(r'console\.log\s*\(', statement):
            explanation = "Displays a message in the browser console."

        elif re.search(r'\.hide\s*\(', statement):
            explanation = "Hides an HTML element."

        elif re.search(r'\.show\s*\(', statement):
            explanation = "Displays an HTML element."

        elif re.search(r'\.val\s*\(', statement):
            explanation = "Gets or changes an element value."

        elif re.search(r'\.submit\s*\(', statement):
            explanation = "Submits a form."

        elif re.search(r'\$\.ajax\s*\(', statement):
            explanation = "Starts an AJAX request."

        elif re.search(r'\bfetch\s*\(', statement):
            explanation = "Starts an HTTP request."

        elif re.search(r'window\.location|location\.href', statement):
            explanation = "Changes the browser URL."

        if explanation:

            results.append({
                "line": current_line,
                "code": statement,
                "explanation": explanation
            })

    return results
