
import re


# =========================================================
# 1. READ PHP FILE
# =========================================================

def read_php_file(file_path):

    try:
        return file_path.read_text(encoding="utf-8")

    except UnicodeDecodeError:
        return file_path.read_text(
            encoding="latin-1",
            errors="replace"
        )

    except OSError:
        return None


# =========================================================
# 2. FIND PHP INPUT VARIABLES
# =========================================================

def detect_php_inputs(code):

    inputs = []

    patterns = {
        "$_POST": r"\$_POST\s*\[\s*['\"]([^'\"]+)['\"]\s*\]",
        "$_GET": r"\$_GET\s*\[\s*['\"]([^'\"]+)['\"]\s*\]",
        "$_REQUEST": r"\$_REQUEST\s*\[\s*['\"]([^'\"]+)['\"]\s*\]"
    }

    for source, pattern in patterns.items():

        for match in re.finditer(pattern, code):

            inputs.append({
                "source": source,
                "field": match.group(1)
            })

    # Detect JSON request body
    if re.search(r"php://input", code, re.IGNORECASE):

        inputs.append({
            "source": "php://input",
            "field": "Raw request body"
        })

        # Find the PHP variable receiving json_decode()
        json_variables = re.findall(
            r"(\$\w+)\s*=\s*json_decode\s*\(",
            code
        )

        for variable in json_variables:

            pattern = (
                re.escape(variable) +
                r"\s*\[\s*['\"]([^'\"]+)['\"]\s*\]"
            )

            for match in re.finditer(pattern, code):

                inputs.append({
                    "source": "Decoded JSON body",
                    "field": match.group(1)
                })

    return inputs


# =========================================================
# 3. DETECT JSON PROCESSING
# =========================================================

def detect_json_processing(code):

    results = []

    if re.search(r"\bjson_decode\s*\(", code):

        results.append(
            "Uses json_decode() to convert JSON into PHP data."
        )

    if re.search(r"\bjson_encode\s*\(", code):

        results.append(
            "Uses json_encode() to convert PHP data into JSON."
        )

    return results


# =========================================================
# 4. DETECT VALIDATION AND CONDITIONS
# =========================================================

def detect_php_conditions(code):

    results = []

    for keyword, description in [
        ("if", "IF condition"),
        ("elseif", "ELSEIF condition")
    ]:

        conditions = extract_parenthesized_conditions(
            code,
            keyword
        )

        for condition in conditions:
            results.append(
                f"{description}: {condition}"
            )

    if re.search(r"\belse\b", code):
        results.append("ELSE branch")

    for pattern, description in [
        (r"\bempty\s*\(", "Checks whether a value is empty"),
        (r"\bisset\s*\(", "Checks whether a variable is set"),
        (r"\bfilter_var\s*\(", "Uses filter_var() for input validation")
    ]:

        for match in re.finditer(pattern, code):

            if "(" in match.group(0):
                results.append(description)

    return results


# =========================================================
# 5. DETECT DATABASE OPERATIONS
# =========================================================

def detect_database_operations(code):

    results = []

    patterns = [
        (
            r"\bnew\s+PDO\s*\(",
            "Creates a database connection using PDO."
        ),
        (
            r"\bmysqli_connect\s*\(",
            "Creates a database connection using MySQLi."
        ),
        (
            r"->\s*prepare\s*\(",
            "Prepares a database SQL statement."
        ),
        (
            r"->\s*query\s*\(",
            "Executes a database query."
        ),
        (
            r"->\s*execute\s*\(",
            "Executes a prepared database statement."
        ),
        (
            r"\bSELECT\b",
            "SQL SELECT operation detected."
        ),
        (
            r"\bINSERT\s+INTO\b",
            "SQL INSERT operation detected."
        ),
        (
            r"\bUPDATE\s+\w+",
            "SQL UPDATE operation detected."
        ),
        (
            r"\bDELETE\s+FROM\b",
            "SQL DELETE operation detected."
        )
    ]

    for pattern, description in patterns:

        if re.search(
            pattern,
            code,
            re.IGNORECASE
        ):

            results.append(description)

    return results


# =========================================================
# 6. DETECT PHP RESPONSES
# =========================================================

def detect_php_responses(code):

    results = []

    if re.search(r"\becho\b", code):

        results.append(
            "Uses echo to send output to the client."
        )

    if re.search(r"\bprint\b", code):

        results.append(
            "Uses print to send output to the client."
        )

    if re.search(r"\bjson_encode\s*\(", code):

        results.append(
            "Sends or prepares a JSON response."
        )

    if re.search(r"\bheader\s*\(", code):

        results.append(
            "Sets an HTTP response header."
        )

    if re.search(r"\bhttp_response_code\s*\(", code):

        results.append(
            "Sets an HTTP response status code."
        )

    return results


# =========================================================
# 7. MATCH JAVASCRIPT DATA WITH PHP INPUTS
# =========================================================


def match_request_data(
    request_data,
    php_inputs,
    javascript_code=""
):
    matches = []

    if not request_data and not javascript_code:
        return matches

    data_keys = []

    # -----------------------------------------------------
    # 1. Extract keys from ordinary JavaScript objects
    # -----------------------------------------------------
    def extract_object_keys(object_code):
        keys = []

        pattern = (
            r"""(?:["']([^"']+)["']|"""
            r"""([A-Za-z_$][\w$]*))\s*:"""
        )

        for match in re.finditer(pattern, object_code):
            key = match.group(1) or match.group(2)
            keys.append(key)

        return keys

    # -----------------------------------------------------
    # 2. Find complete JSON.stringify({...}) objects
    # -----------------------------------------------------
    if javascript_code:
        stringify_pattern = re.compile(
            r"JSON\.stringify\s*\(\s*\{",
            re.IGNORECASE
        )

        for match in stringify_pattern.finditer(javascript_code):

            opening_index = javascript_code.find(
                "{",
                match.start()
            )

            # Find the matching closing brace.
            depth = 0
            quote = None
            closing_index = -1
            i = opening_index

            while i < len(javascript_code):
                char = javascript_code[i]

                if quote:
                    if char == "\\":
                        i += 2
                        continue

                    if char == quote:
                        quote = None

                elif char in ("'", '"', "`"):
                    quote = char

                elif char == "{":
                    depth += 1

                elif char == "}":
                    depth -= 1

                    if depth == 0:
                        closing_index = i
                        break

                i += 1

            if closing_index != -1:
                object_code = javascript_code[
                    opening_index + 1:closing_index
                ]

                data_keys.extend(
                    extract_object_keys(object_code)
                )

    # -----------------------------------------------------
    # 3. Extract keys from the supplied request data
    # -----------------------------------------------------
    if request_data:
        data_keys.extend(
            extract_object_keys(request_data)
        )

    # -----------------------------------------------------
    # 4. Remove duplicate field names
    # -----------------------------------------------------
    data_keys = list(dict.fromkeys(data_keys))

    # -----------------------------------------------------
    # 5. Collect PHP input field names
    # -----------------------------------------------------
    php_fields = {
        item["field"]
        for item in php_inputs
    }

    # -----------------------------------------------------
    # 6. Compare JavaScript fields with PHP inputs
    # -----------------------------------------------------
    if not data_keys:
        return matches

    for key in data_keys:

        if key in php_fields:
            matches.append(
                f"JavaScript field '{key}' "
                f"matches PHP input '{key}'."
            )

        else:
            matches.append(
                f"JavaScript field '{key}' "
                f"has no matching PHP input detected."
            )

    return matches



# =========================================================
# 8. ANALYZE PHP ENDPOINT
# =========================================================

def analyze_php_file(file_path, request_data=None, javascript_code=""):

    code = read_php_file(file_path)

    if code is None:

        return {
            "exists": False,
            "messages": [
                "PHP endpoint file could not be read."
            ]
        }

    messages = []

    php_inputs = detect_php_inputs(code)

    json_processing = detect_json_processing(code)

    conditions = detect_php_conditions(code)

    database_operations = detect_database_operations(code)

    responses = detect_php_responses(code)

    # Input analysis
    messages.append("PHP INPUT ANALYSIS")

    if php_inputs:

        for item in php_inputs:

            messages.append(
                f"Receives {item['field']} through {item['source']}."
            )

    else:

        messages.append(
            "No supported PHP input variables detected."
        )

    # JSON analysis
    messages.append("\nJSON PROCESSING")

    if json_processing:

        messages.extend(json_processing)

    else:

        messages.append(
            "No JSON processing detected."
        )

    # Validation analysis
    messages.append("\nVALIDATION AND CONDITIONS")

    if conditions:

        messages.extend(conditions)

    else:

        messages.append(
            "No supported validation conditions detected."
        )

    # Database analysis
    messages.append("\nDATABASE OPERATIONS")

    if database_operations:

        messages.extend(database_operations)

    else:

        messages.append(
            "No supported database operations detected."
        )

    # Response analysis
    messages.append("\nPHP RESPONSE ANALYSIS")

    if responses:

        messages.extend(responses)

    else:

        messages.append(
            "No supported PHP response statements detected."
        )

    # Match frontend request fields with PHP inputs
    messages.append("\nFRONTEND-TO-BACKEND DATA MATCHING")

    if request_data:

        matches = match_request_data(
            request_data,
            php_inputs,
            javascript_code
        )

        if matches:

            messages.extend(matches)

        else:

            messages.append(
                "No JavaScript request field names could be matched."
            )

    else:

        messages.append(
            "No request data available for comparison."
        )

    return {
        "exists": True,
        "messages": messages
    }

def extract_parenthesized_conditions(code, keyword):

    results = []

    pattern = rf"\b{keyword}\s*\("

    for match in re.finditer(pattern, code):

        start = match.end()
        depth = 1
        position = start

        while position < len(code) and depth > 0:

            char = code[position]

            if char == "(":
                depth += 1

            elif char == ")":
                depth -= 1

            position += 1

        if depth == 0:
            condition = code[start:position - 1].strip()
            results.append(condition)

    return results