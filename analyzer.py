
import re


# =========================================================
# JAVASCRIPT KEYWORDS AND BUILT-IN FUNCTIONS
# =========================================================

IGNORED_CALLS = {
    # JavaScript keywords
    "if", "else", "for", "while", "switch",
    "catch", "function", "return", "typeof",
    "new", "throw", "try", "do", "await",
    "delete", "void",

    # Browser built-ins
    "alert", "confirm", "prompt",
    "parseInt", "parseFloat",
    "setTimeout", "setInterval",
    "clearTimeout", "clearInterval",
    "fetch",

    # AJAX and jQuery methods
    "ajax", "get", "post",

    # Promise methods
    "then", "catch",

    # JSON methods
    "JSON", "stringify", "parse",

    # Console methods
    "log", "error", "warn", "info",

    # jQuery selector
    "$", "jQuery"
}


# =========================================================
# 1. FIND MATCHING BRACE
# =========================================================

def find_matching_brace(code, open_pos):

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


# =========================================================
# 2. EXTRACT FUNCTION DEFINITIONS
# =========================================================

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

        close_pos = find_matching_brace(
            code,
            open_pos
        )

        if close_pos is None:
            continue

        body = code[open_pos + 1:close_pos]

        line = (
            start_line +
            code[:match.start()].count("\n")
        )

        functions.append({
            "name": name,
            "parameters": parameters,
            "line": line,
            "body": body
        })

    return functions


# =========================================================
# 3. EXTRACT FUNCTION CALLS
# =========================================================

def extract_function_calls(code):

    calls = []

    pattern = re.compile(
        r'(?<![.\w$])([A-Za-z_$][\w$]*)\s*\('
    )

    for match in pattern.finditer(code):

        name = match.group(1)

        if name in IGNORED_CALLS:
            continue

        prefix = code[:match.start()].rstrip()

        # Ignore function declarations
        if re.search(r'\bfunction\s*$', prefix):
            continue

        # Ignore object methods
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


# =========================================================
# 4. EXTRACT EVENT HANDLERS
# =========================================================

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

            close_pos = find_matching_brace(
                code,
                open_pos
            )

            if close_pos is None:
                continue

            body = code[open_pos + 1:close_pos]

            line = (
                start_line +
                code[:match.start()].count("\n")
            )

            selector = "Unknown element"
            before = code[:match.start()]

            # jQuery selector
            if event_type == "jQuery":

                selector_match = re.search(
                    r'(\$\s*\(\s*["\'][^"\']+["\']\s*\))\s*$',
                    before
                )

                if selector_match:
                    selector = selector_match.group(1)

            # DOM getElementById selector
            else:

                id_match = re.search(
                    r'document\s*\.\s*getElementById\s*'
                    r'\(\s*["\']([^"\']+)["\']\s*\)\s*$',
                    before
                )

                if id_match:
                    selector = "#" + id_match.group(1)

                else:

                    # DOM querySelector selector
                    query_match = re.search(
                        r'document\s*\.\s*querySelector\s*'
                        r'\(\s*["\']([^"\']+)["\']\s*\)\s*$',
                        before
                    )

                    if query_match:
                        selector = query_match.group(1)

            events.append({
                "event": event_name,
                "type": event_type,
                "selector": selector,
                "line": line,
                "body": body
            })

    return events


# =========================================================
# 5. BUILD FUNCTION CALL GRAPH
# =========================================================

def build_call_graph(functions):

    graph = {}

    for function in functions:

        calls = extract_function_calls(
            function["body"]
        )

        graph[function["name"]] = calls

    return graph



# =========================================================
# 6. FIND ASYNCHRONOUS CALLBACK BLOCKS
# =========================================================

def find_async_callback_ranges(body):

    callback_patterns = [

        # AJAX success callback
        (
            r'\bsuccess\s*:\s*function\s*'
            r'\([^)]*\)\s*\{',
            "AJAX success callback"
        ),

        # AJAX error callback
        (
            r'\berror\s*:\s*function\s*'
            r'\([^)]*\)\s*\{',
            "AJAX error callback"
        ),

        # Promise then callback
        (
            r'\.then\s*\(\s*'
            r'(?:function\s*\([^)]*\)|'
            r'(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)'
            r'\s*\{',
            "Promise then() callback"
        ),

        # Promise catch callback
        (
            r'\.catch\s*\(\s*'
            r'(?:function\s*\([^)]*\)|'
            r'(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>)'
            r'\s*\{',
            "Promise catch() callback"
        )
    ]

    ranges = {}

    # Detect standard AJAX and Promise callbacks
    for pattern, label in callback_patterns:

        for match in re.finditer(pattern, body):

            open_pos = match.end() - 1

            close_pos = find_matching_brace(
                body,
                open_pos
            )

            if close_pos is None:
                continue

            start_line = body[:match.start()].count("\n")
            end_line = body[:close_pos].count("\n")

            ranges[start_line] = {
                "end_line": end_line,
                "label": label
            }

    # -----------------------------------------------------
    # Detect jQuery $.get() and $.post() success callbacks
    # -----------------------------------------------------

    jquery_pattern = re.compile(
        r'\$\s*\.\s*(?:get|post)\s*\('
        r'[^;]*?'
        r'(\bfunction\s*\([^)]*\)\s*\{)',
        re.DOTALL
    )

    for match in re.finditer(jquery_pattern, body):

        callback_start = match.start(1)
        open_pos = match.end(1) - 1

        close_pos = find_matching_brace(
            body,
            open_pos
        )

        if close_pos is None:
            continue

        start_line = body[:callback_start].count("\n")
        end_line = body[:close_pos].count("\n")

        ranges[start_line] = {
            "end_line": end_line,
            "label": "jQuery success callback"
        }

    return ranges



# =========================================================
# 7. TRACE FUNCTION EXECUTION
# =========================================================

def trace_function(
    name,
    function_map,
    graph,
    visited=None,
    depth=0
):

    if visited is None:
        visited = set()

    if name in visited:

        return [{
            "depth": depth,
            "message": (
                f"{name}() already visited. Possible recursion."
            )
        }]

    if name not in function_map:

        return [{
            "depth": depth,
            "message": (
                f"{name}() definition not found in this file."
            )
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

    branch_stack = []

    # Find asynchronous callback blocks
    callback_ranges = find_async_callback_ranges(body)

    index = 0

    while index < len(lines):

        line = lines[index]
        statement = line.strip()

        if not statement or statement.startswith("//"):
            index += 1
            continue

        # Asynchronous callback detection
        if index in callback_ranges:

            callback = callback_ranges[index]

            current_depth = depth + 1 + len(branch_stack)

            results.append({
                "depth": current_depth,
                "message": (
                    f"Registers {callback['label']}. "
                    "Its code runs asynchronously when "
                    "the corresponding response or promise event occurs."
                )
            })

            # Skip callback body because it does not execute immediately
            index = callback["end_line"] + 1
            continue

        # Close previous branches
        leading_closes = (
            len(statement) -
            len(statement.lstrip("}"))
        )

        for _ in range(leading_closes):

            if branch_stack:
                branch_stack.pop()

        statement = statement.lstrip("}").strip()

        if not statement:
            index += 1
            continue

        current_depth = depth + 1 + len(branch_stack)

        # Conditions
        else_if_match = re.match(
            r'else\s+if\s*\((.*)\)\s*\{?',
            statement
        )

        if_match = re.match(
            r'if\s*\((.*)\)\s*\{?',
            statement
        )

        is_else = re.match(
            r'else\s*\{?',
            statement
        )

        if else_if_match or if_match:

            condition = (
                else_if_match.group(1).strip()
                if else_if_match
                else if_match.group(1).strip()
            )

            if else_if_match:

                results.append({
                    "depth": current_depth,
                    "message": (
                        f"Checks ELSE IF condition: {condition}. "
                        "This is evaluated when the previous "
                        "IF branch was not taken."
                    )
                })

            else:

                results.append({
                    "depth": current_depth,
                    "message": f"Checks IF condition: {condition}."
                })

            # Trace function calls inside conditions
            condition_calls = extract_function_calls(condition)

            for call in condition_calls:

                called_name = call["name"]

                results.append({
                    "depth": current_depth + 1,
                    "message": (
                        f"Calls {called_name}() "
                        "to evaluate the condition."
                    )
                })

                if called_name in function_map:

                    nested = trace_function(
                        called_name,
                        function_map,
                        graph,
                        visited,
                        current_depth + 2
                    )

                    results.extend(nested)

                else:

                    results.append({
                        "depth": current_depth + 2,
                        "message": (
                            f"{called_name}() definition not found "
                            "in this input file."
                        )
                    })

            branch_type = (
                "ELSE IF"
                if else_if_match
                else "IF"
            )

            results.append({
                "depth": current_depth + 1,
                "message": (
                    f"If this {branch_type} condition is TRUE, "
                    "executes this branch."
                )
            })

            branch_stack.append(branch_type)

        elif is_else:

            results.append({
                "depth": current_depth,
                "message": (
                    "If the preceding IF condition is FALSE, "
                    "executes this ELSE branch."
                )
            })

            branch_stack.append("ELSE")

        # Return statement
        return_match = re.match(
            r'return(?:\s+(.*?))?;?$',
            statement
        )

        if return_match:

            return_value = return_match.group(1)

            if return_value:

                results.append({
                    "depth": current_depth,
                    "message": (
                        f"Returns {return_value.rstrip(';')} "
                        "from the function and exits this function."
                    )
                })

            else:

                results.append({
                    "depth": current_depth,
                    "message": (
                        "Returns from the function and exits this function."
                    )
                })

        # AJAX request
        if re.search(r'\$\s*\.\s*ajax\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": (
                    "Starts an AJAX request to a backend endpoint."
                )
            })

        # Fetch request
        elif re.search(r'\bfetch\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": (
                    "Starts an HTTP request using Fetch."
                )
            })

        # jQuery selector
        elif re.search(r'\$\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": (
                    "Selects an HTML element using jQuery."
                )
            })

        # Console output
        if re.search(r'console\.log\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": (
                    "Displays a message in the browser console."
                )
            })

        # Form submission
        if re.search(r'\.submit\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": (
                    "Submits the selected HTML form."
                )
            })

        # Show and hide
        if re.search(r'\.hide\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": "Hides an HTML element."
            })

        if re.search(r'\.show\s*\(', statement):

            results.append({
                "depth": current_depth,
                "message": "Displays an HTML element."
            })

        # Browser navigation
        if re.search(
            r'window\.location|location\.href',
            statement
        ):

            results.append({
                "depth": current_depth,
                "message": "Changes the browser URL."
            })

        # Function calls
        if if_match or else_if_match:
            calls = []
        else:
            calls = extract_function_calls(statement)

        for call in calls:

            called_name = call["name"]

            results.append({
                "depth": current_depth,
                "message": f"Calls {called_name}()."
            })

            if called_name in function_map:

                nested = trace_function(
                    called_name,
                    function_map,
                    graph,
                    visited,
                    current_depth + 1
                )

                results.extend(nested)

            else:

                results.append({
                    "depth": current_depth + 1,
                    "message": (
                        f"{called_name}() definition not found "
                        "in this input file."
                    )
                })

        index += 1

    return results



# =========================================================
# 8. EXPLAIN JAVASCRIPT STATEMENTS
# =========================================================

def analyze_javascript(code, start_line=1):

    results = []

    lines = code.splitlines()

    # Identify asynchronous callback blocks
    callback_ranges = find_async_callback_ranges(code)

    # Collect callback body lines that should not be
    # reported as immediate execution.
    skipped_lines = set()

    for start, callback in callback_ranges.items():

        end = callback["end_line"]

        for line_number in range(start + 1, end + 1):
            skipped_lines.add(line_number)

    for index, line in enumerate(lines):

        # Skip lines inside asynchronous callbacks
        if index in skipped_lines:
            continue

        current_line = start_line + index
        statement = line.strip()

        if not statement or statement.startswith("//"):
            continue

        explanation = None

        # Event registration
        event_match = re.search(
            r'\.on\s*\(\s*["\'](\w+)["\']',
            statement
        )

        if event_match:

            explanation = (
                f"Registers a {event_match.group(1)} event handler."
            )

        # Function declaration
        elif re.match(r'^function\s+\w+', statement):

            match = re.search(
                r'function\s+(\w+)',
                statement
            )

            explanation = (
                f"Defines the function {match.group(1)}."
            )

        # ELSE IF
        elif re.match(r'^else\s+if\s*\(', statement):

            explanation = "Checks an ELSE IF condition."

        # IF
        elif re.match(r'^if\s*\(', statement):

            explanation = "Checks an IF condition."

        # ELSE
        elif re.match(r'^else\b', statement):

            explanation = "Executes an alternative ELSE branch."

        # AJAX
        elif re.search(r'\$\s*\.\s*ajax\s*\(', statement):

            explanation = "Starts an AJAX request."

        # Fetch
        elif re.search(r'\bfetch\s*\(', statement):

            explanation = "Starts an HTTP request."

        # jQuery selector
        elif re.search(r'\$\s*\(', statement):

            explanation = (
                "Selects an HTML element using a jQuery selector."
            )

        # Console output
        elif re.search(r'console\.log\s*\(', statement):

            explanation = (
                "Displays a message in the browser console."
            )

        # Hide
        elif re.search(r'\.hide\s*\(', statement):

            explanation = "Hides an HTML element."

        # Show
        elif re.search(r'\.show\s*\(', statement):

            explanation = "Displays an HTML element."

        # Value
        elif re.search(r'\.val\s*\(', statement):

            explanation = "Gets or changes an element value."

        # Form submission
        elif re.search(r'\.submit\s*\(', statement):

            explanation = "Submits a form."

        # Browser navigation
        elif re.search(
            r'window\.location|location\.href',
            statement
        ):

            explanation = "Changes the browser URL."

        # Return
        elif re.match(r'^return\b', statement):

            explanation = (
                "Returns a value from the current function."
            )

        if explanation:

            results.append({

                "line": current_line,
                "code": statement,
                "explanation": explanation

            })

    return results
