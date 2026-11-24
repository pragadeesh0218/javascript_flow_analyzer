
import re

from analyzer import extract_function_calls
from backend_analyzer import detect_backend_requests


def create_function_lookup(functions):
    return {
        function["name"]: function
        for function in functions
    }


def find_form_submissions(code, forms):
    """Return forms associated with submit() or requestSubmit()."""
    matched_forms = []

    if not code:
        return matched_forms

    submit_found = re.search(
        r"\.\s*(?:submit|requestSubmit)\s*\(",
        code,
        re.IGNORECASE
    )

    if not submit_found:
        return matched_forms

    for form in forms:
        form_id = form.get("id", "")

        if not form_id:
            continue

        patterns = [
            rf"""#\s*["']?{re.escape(form_id)}["']?""",
            rf"""getElementById\s*\(\s*["']{re.escape(form_id)}["']\s*\)""",
            rf"""querySelector\s*\(\s*["']#{re.escape(form_id)}["']\s*\)"""
        ]

        if any(re.search(pattern, code) for pattern in patterns):
            matched_forms.append(form)

    if not matched_forms and len(forms) == 1:
        matched_forms.append(forms[0])

    return matched_forms


def get_line_column(code, position, start_line):
    """Convert a character position into an absolute line and column."""
    preceding_text = code[:position]
    line_offset = preceding_text.count("\n")

    last_newline = preceding_text.rfind("\n")
    column = position if last_newline == -1 else position - last_newline - 1

    return start_line + line_offset, column


def collect_ordered_actions(code, start_line, function_map, forms):
    """
    Collect local function calls, backend requests and form submissions,
    then sort them by their position in the source code.
    """
    actions = []

    if not code:
        return actions

    # 1. Find calls to locally defined functions.
    function_calls = extract_function_calls(code)

    for call in function_calls:
        name = call["name"]

        if name not in function_map:
            continue

        pattern = re.compile(
            rf"(?<![\w$.]){re.escape(name)}\s*\("
        )

        for match in pattern.finditer(code):
            # Ignore a named function declaration if one appears in this body.
            line_start = code.rfind("\n", 0, match.start()) + 1
            prefix = code[line_start:match.start()]

            if re.search(r"\bfunction\s*$", prefix):
                continue

            line, column = get_line_column(
                code,
                match.start(),
                start_line
            )

            actions.append({
                "sort_line": line,
                "sort_column": column,
                "type": "call",
                "name": name,
                "message": f"Calls {name}()."
            })

            # The existing extractor returns unique function names.
            # Keep only the first occurrence to avoid duplicate traces.
            break

    # 2. Find AJAX and Fetch requests.
    requests = detect_backend_requests(code, start_line)

    for request in requests:
        request_line = request.get("line", start_line)
        local_line_index = request_line - start_line
        code_lines = code.splitlines()

        column = 0

        if 0 <= local_line_index < len(code_lines):
            request_line_text = code_lines[local_line_index]
            request_match = re.search(
                r"\bfetch\s*\(|\$\s*\.\s*(?:ajax|get|post)\s*\(",
                request_line_text,
                re.IGNORECASE
            )

            if request_match:
                column = request_match.start()

        request_type = request.get("type", "Request")
        method = request.get("method", "Unknown")
        endpoint = request.get("endpoint", "Unknown")

        actions.append({
            "sort_line": request_line,
            "sort_column": column,
            "type": "request",
            "endpoint": endpoint,
            "message": (
                f"{request_type} request ({method}) to {endpoint}."
            )
        })

    # 3. Find form submissions and their source positions.
    submitted_forms = find_form_submissions(code, forms)

    if submitted_forms:
        submit_pattern = re.compile(
            r"\.\s*(?:submit|requestSubmit)\s*\(",
            re.IGNORECASE
        )

        for match in submit_pattern.finditer(code):
            line, column = get_line_column(
                code,
                match.start(),
                start_line
            )

            for form in submitted_forms:
                action = form.get("action") or "(no action specified)"
                method = form.get("method", "GET")

                actions.append({
                    "sort_line": line,
                    "sort_column": column,
                    "type": "form",
                    "endpoint": action,
                    "message": (
                        f"HTML form submission ({method}) to {action}."
                    )
                })

    actions.sort(
        key=lambda item: (
            item["sort_line"],
            item["sort_column"]
        )
    )

    return actions


def trace_function_backend_flow(
    function_name,
    function_map,
    forms,
    depth=0,
    call_path=None,
    max_depth=10
):
    if call_path is None:
        call_path = []

    results = []

    if function_name not in function_map:
        return results

    if function_name in call_path:
        results.append({
            "depth": depth,
            "type": "info",
            "message": (
                f"Possible recursion detected in {function_name}()."
            )
        })
        return results

    if depth >= max_depth:
        results.append({
            "depth": depth,
            "type": "info",
            "message": "Maximum function tracing depth reached."
        })
        return results

    function = function_map[function_name]
    body = function.get("body", "")
    function_start_line = function.get("line", 1) + 1

    results.append({
        "depth": depth,
        "type": "function",
        "message": (
            f"Function {function_name}() "
            f"defined at line {function['line']}."
        )
    })

    actions = collect_ordered_actions(
        body,
        function_start_line,
        function_map,
        forms
    )

    next_path = call_path + [function_name]

    # Process calls and backend actions in their source order.
    for action in actions:
        action_type = action["type"]

        if action_type == "call":
            called_name = action["name"]

            results.append({
                "depth": depth + 1,
                "type": "call",
                "message": action["message"]
            })

            results.extend(
                trace_function_backend_flow(
                    called_name,
                    function_map,
                    forms,
                    depth + 2,
                    next_path,
                    max_depth
                )
            )

        else:
            results.append({
                "depth": depth + 1,
                "type": action_type,
                "endpoint": action.get("endpoint"),
                "message": action["message"]
            })

    return results


def build_backend_execution_flow(events, functions, forms):
    function_map = create_function_lookup(functions)
    execution_flows = []

    for event in events:
        event_body = event.get("body", "")
        event_start_line = event.get("line", 1)

        flow = {
            "event": event.get("event", "Unknown"),
            "type": event.get("type", "Unknown"),
            "element": event.get("selector", "Unknown"),
            "line": event.get("line"),
            "steps": []
        }

        actions = collect_ordered_actions(
            event_body,
            event_start_line,
            function_map,
            forms
        )

        for action in actions:
            if action["type"] == "call":
                called_name = action["name"]

                flow["steps"].append({
                    "depth": 0,
                    "type": "call",
                    "message": f"Event calls {called_name}()."
                })

                flow["steps"].extend(
                    trace_function_backend_flow(
                        called_name,
                        function_map,
                        forms,
                        depth=1
                    )
                )

            else:
                flow["steps"].append({
                    "depth": 0,
                    "type": action["type"],
                    "endpoint": action.get("endpoint"),
                    "message": action["message"]
                })

        execution_flows.append(flow)

    return execution_flows
