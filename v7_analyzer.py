
# ==================== v7_analyzer.py ====================

from analyzer import extract_function_calls


# =========================================================
# 1. CREATE FUNCTION LOOKUP
# =========================================================

def create_function_lookup(functions):

    function_map = {}

    for function in functions:
        function_map[function["name"]] = function

    return function_map


# =========================================================
# 2. TRACE NESTED FUNCTION CALLS
# =========================================================

def trace_call_chain(
    function_name,
    function_map,
    depth=0,
    call_path=None,
    max_depth=10
):

    if call_path is None:
        call_path = []

    results = []

    # Check whether function exists
    if function_name not in function_map:

        results.append({
            "depth": depth,
            "message": (
                f"{function_name}() definition not found "
                "in this input file. It may be external."
            )
        })

        return results

    # Detect recursion
    if function_name in call_path:

        results.append({
            "depth": depth,
            "message": (
                f"{function_name}() calls itself directly "
                "or indirectly. Possible recursion detected."
            )
        })

        return results

    # Prevent excessive tracing
    if depth >= max_depth:

        results.append({
            "depth": depth,
            "message": "Maximum function tracing depth reached."
        })

        return results

    function = function_map[function_name]

    results.append({
        "depth": depth,
        "message": (
            f"Function {function_name}() "
            f"defined at line {function['line']}."
        )
    })

    # Extract calls inside this function
    calls = extract_function_calls(
        function["body"]
    )

    next_path = call_path + [function_name]

    for call in calls:

        called_name = call["name"]

        if called_name in function_map:

            results.append({
                "depth": depth + 1,
                "message": f"Calls {called_name}()."
            })

            nested_results = trace_call_chain(
                called_name,
                function_map,
                depth + 2,
                next_path,
                max_depth
            )

            results.extend(nested_results)

        else:

            results.append({
                "depth": depth + 1,
                "message": (
                    f"Calls {called_name}(), but its definition "
                    "was not found in this input file."
                )
            })

    return results


# =========================================================
# 3. BUILD EVENT-TO-FUNCTION EXECUTION FLOW
# =========================================================

def build_execution_flow(events, functions):

    function_map = create_function_lookup(functions)

    execution_flows = []

    for event in events:

        flow = {
            "event": event["event"],
            "type": event["type"],
            "element": event["selector"],
            "line": event["line"],
            "steps": []
        }

        # Find function calls inside the event handler
        calls = extract_function_calls(
            event["body"]
        )

        if not calls:

            flow["steps"].append({
                "depth": 0,
                "message": (
                    "No function calls detected inside "
                    "this event handler."
                )
            })

        for call in calls:

            called_name = call["name"]

            if called_name in function_map:

                flow["steps"].append({
                    "depth": 0,
                    "message": f"Event calls {called_name}()."
                })

                nested_results = trace_call_chain(
                    called_name,
                    function_map,
                    depth=1
                )

                flow["steps"].extend(nested_results)

            else:

                flow["steps"].append({
                    "depth": 0,
                    "message": (
                        f"Event calls {called_name}(), but its "
                        "definition was not found in this file."
                    )
                })

        execution_flows.append(flow)

    return execution_flows
