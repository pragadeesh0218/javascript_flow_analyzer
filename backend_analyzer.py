
import re


# ---------------------------------------------------------
# 1. MATCHING DELIMITERS
# ---------------------------------------------------------

def find_matching_delimiter(code, opening_index, opening, closing):

    depth = 0
    quote = None
    i = opening_index

    while i < len(code):

        char = code[i]
        next_char = code[i + 1] if i + 1 < len(code) else ""

        # Single-line comments
        if quote is None and char == "/" and next_char == "/":

            newline = code.find("\n", i)

            if newline == -1:
                return -1

            i = newline + 1
            continue

        # Multi-line comments
        if quote is None and char == "/" and next_char == "*":

            end_comment = code.find("*/", i + 2)

            if end_comment == -1:
                return -1

            i = end_comment + 2
            continue

        # Strings
        if quote:

            if char == "\\":
                i += 2
                continue

            if char == quote:
                quote = None

            i += 1
            continue

        if char in ("'", '"', "`"):
            quote = char

        elif char == opening:
            depth += 1

        elif char == closing:

            depth -= 1

            if depth == 0:
                return i

        i += 1

    return -1


# ---------------------------------------------------------
# 2. SPLIT ARGUMENTS WITHOUT BREAKING NESTED OBJECTS
# ---------------------------------------------------------

def split_top_level(text, delimiter=","):

    parts = []
    stack = []
    quote = None

    pairs = {
        ")": "(",
        "}": "{",
        "]": "["
    }

    start = 0
    i = 0

    while i < len(text):

        char = text[i]

        if quote:

            if char == "\\":
                i += 2
                continue

            if char == quote:
                quote = None

        elif char in ("'", '"', "`"):

            quote = char

        elif char in ("(", "{", "["):

            stack.append(char)

        elif char in (")", "}", "]"):

            if stack and stack[-1] == pairs[char]:
                stack.pop()

        elif char == delimiter and not stack:

            parts.append(text[start:i].strip())
            start = i + 1

        i += 1

    parts.append(text[start:].strip())

    return parts


# ---------------------------------------------------------
# 3. EXTRACT STRING VALUES
# ---------------------------------------------------------

def extract_first_string(expression):

    if not expression:
        return ""

    expression = expression.strip()

    if not expression or expression[0] not in ("'", '"', "`"):
        return expression

    quote = expression[0]
    i = 1

    while i < len(expression):

        if expression[i] == "\\":
            i += 2
            continue

        if expression[i] == quote:
            return expression[1:i]

        i += 1

    return expression


# ---------------------------------------------------------
# 4. EXTRACT OBJECT PROPERTY VALUES
# ---------------------------------------------------------

def extract_property_value(code, property_name):

    pattern = rf'\b{re.escape(property_name)}\s*:'

    match = re.search(pattern, code, re.IGNORECASE)

    if not match:
        return None

    start = match.end()

    while start < len(code) and code[start].isspace():
        start += 1

    if start >= len(code):
        return None

    first_char = code[start]

    # Object or array
    if first_char in ("{", "["):

        closing = "}" if first_char == "{" else "]"

        end = find_matching_delimiter(
            code,
            start,
            first_char,
            closing
        )

        if end != -1:
            return code[start:end + 1].strip()

    # String
    if first_char in ("'", '"', "`"):

        quote = first_char
        i = start + 1

        while i < len(code):

            if code[i] == "\\":
                i += 2
                continue

            if code[i] == quote:
                return code[start:i + 1].strip()

            i += 1

    # Simple expression
    end = start

    while end < len(code) and code[end] not in ",\n}":
        end += 1

    return code[start:end].strip()


# ---------------------------------------------------------
# 5. DESCRIBE BACKEND ENDPOINT
# ---------------------------------------------------------

def describe_endpoint(value):

    if not value:
        return "Not identified"

    endpoint = extract_first_string(value)

    if ".php" in endpoint.lower():
        return endpoint

    if endpoint.startswith(("/", "./", "../")):
        return endpoint

    if value.strip().startswith(("'", '"', "`")):
        return endpoint

    return f"Dynamic endpoint: {endpoint}"


# ---------------------------------------------------------
# 6. EXTRACT COMPLETE PROMISE CHAIN
# ---------------------------------------------------------

def extract_promise_chain(code, start_index):

    stack = []
    quote = None

    line_comment = False
    block_comment = False

    i = start_index

    while i < len(code):

        char = code[i]
        next_char = code[i + 1] if i + 1 < len(code) else ""

        # Single-line comments
        if line_comment:

            if char == "\n":
                line_comment = False

            i += 1
            continue

        # Multi-line comments
        if block_comment:

            if char == "*" and next_char == "/":
                block_comment = False
                i += 2
                continue

            i += 1
            continue

        # Strings
        if quote:

            if char == "\\":
                i += 2
                continue

            if char == quote:
                quote = None

            i += 1
            continue

        # Comments
        if char == "/" and next_char == "/":
            line_comment = True
            i += 2
            continue

        if char == "/" and next_char == "*":
            block_comment = True
            i += 2
            continue

        # String start
        if char in ("'", '"', "`"):
            quote = char
            i += 1
            continue

        # Nested delimiters
        if char in ("(", "{", "["):

            stack.append(char)

        elif char in (")", "}", "]"):

            if stack:
                stack.pop()

        # Stop only at a top-level semicolon
        elif char == ";" and not stack:

            return code[start_index:i]

        i += 1

    return code[start_index:]


# ---------------------------------------------------------
# 7. DETECT BACKEND REQUESTS
# ---------------------------------------------------------

def detect_backend_requests(code, start_line=1):

    requests = []

    patterns = [
        ("AJAX", r'\$\s*\.\s*ajax\s*\('),
        ("FETCH", r'\bfetch\s*\('),
        ("JQUERY_GET", r'\$\s*\.\s*get\s*\('),
        ("JQUERY_POST", r'\$\s*\.\s*post\s*\(')
    ]

    for request_type, pattern in patterns:

        for match in re.finditer(pattern, code, re.IGNORECASE):

            opening_index = code.find("(", match.start())

            closing_index = find_matching_delimiter(
                code,
                opening_index,
                "(",
                ")"
            )

            if closing_index == -1:
                continue

            arguments = code[opening_index + 1:closing_index]

            if not arguments.strip():
                continue

            line = (
                start_line +
                code[:match.start()].count("\n")
            )

            endpoint = None
            method = None
            request_data = None

            response_handling = []

            # ---------------------------------------------
            # AJAX
            # ---------------------------------------------

            if request_type == "AJAX":

                endpoint = extract_property_value(
                    arguments,
                    "url"
                )

                method = (
                    extract_property_value(arguments, "type")
                    or extract_property_value(arguments, "method")
                )

                request_data = extract_property_value(
                    arguments,
                    "data"
                )

                method = (
                    extract_first_string(method).upper()
                    if method
                    else "GET (default)"
                )

                if re.search(r'\bsuccess\s*:', arguments):

                    response_handling.append(
                        "AJAX success callback"
                    )

                if re.search(r'\berror\s*:', arguments):

                    response_handling.append(
                        "AJAX error callback"
                    )

            # ---------------------------------------------
            # FETCH
            # ---------------------------------------------

            elif request_type == "FETCH":

                parts = split_top_level(arguments)

                endpoint = parts[0] if parts else None

                options = parts[1] if len(parts) > 1 else ""

                method = extract_property_value(
                    options,
                    "method"
                )

                request_data = extract_property_value(
                    options,
                    "body"
                )

                method = (
                    extract_first_string(method).upper()
                    if method
                    else "GET (default)"
                )

                # Read the entire Promise chain.
                # Semicolons inside callbacks are ignored.
                promise_chain = extract_promise_chain(
                    code,
                    closing_index + 1
                )

                # Detect all supported Promise handlers.
                if re.search(r'\.then\s*\(', promise_chain):

                    response_handling.append(
                        "Promise then() handler"
                    )

                if re.search(r'\.catch\s*\(', promise_chain):

                    response_handling.append(
                        "Promise catch() handler"
                    )

            # ---------------------------------------------
            # JQUERY GET / POST
            # ---------------------------------------------

            else:

                parts = split_top_level(arguments)

                endpoint = parts[0] if parts else None

                method = (
                    "GET"
                    if request_type == "JQUERY_GET"
                    else "POST"
                )

                if len(parts) > 1:
                    request_data = parts[1]

                if len(parts) > 2:

                    response_handling.append(
                        "jQuery success callback"
                    )

            if not response_handling:

                response_handling.append(
                    "No supported response handler identified"
                )

            requests.append({

                "line": line,

                "type": request_type,

                "endpoint": describe_endpoint(endpoint),

                "method": method,

                "data": (
                    request_data
                    if request_data
                    else "No request data identified"
                ),

                "response_handling": response_handling

            })

    return requests
