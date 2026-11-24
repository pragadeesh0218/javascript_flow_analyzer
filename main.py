
from pathlib import Path
from urllib.parse import urlsplit

from backend_analyzer import detect_backend_requests
from php_analyzer import analyze_php_file

from parser import extract_javascript

from analyzer import (
    analyze_javascript,
    extract_functions,
    extract_function_calls,
    extract_event_handlers,
    build_call_graph,
    trace_function
)

from explainer import generate_report


# =========================================================
# CONFIGURATION
# =========================================================

INPUT_FILE = "input/v5_test3_database.html"
OUTPUT_FILE = "output/flow_report.txt"


# =========================================================
# FIND LOCAL PHP ENDPOINT
# =========================================================

def resolve_php_endpoint(endpoint, input_path):

    if not endpoint:
        return None

    # Ignore dynamic endpoints
    if endpoint.startswith("Dynamic endpoint:"):
        return None

    endpoint_path = urlsplit(endpoint).path

    if not endpoint_path.lower().endswith(".php"):
        return None

    # Resolve relative to the HTML input directory
    php_path = (
        input_path.parent /
        endpoint_path.lstrip("/")
    ).resolve()

    return php_path


# =========================================================
# MAIN
# =========================================================

def main():

    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():

        print("Input file not found!")
        return

    print("Starting JavaScript Flow Analyzer...")

    parsed_data = extract_javascript(input_path)

    all_functions = []
    all_events = []
    analysis_results = []
    all_backend_requests = []
    all_javascript_code = []

    # -----------------------------------------------------
    # 1. ANALYZE INTERNAL JAVASCRIPT
    # -----------------------------------------------------

    for script in parsed_data["scripts"]:

        code = script["code"]
        all_javascript_code.append(code)
        start_line = script["line"]

        all_functions.extend(
            extract_functions(code, start_line)
        )

        all_events.extend(
            extract_event_handlers(code, start_line)
        )

        analysis_results.extend(
            analyze_javascript(code, start_line)
        )

        all_backend_requests.extend(
            detect_backend_requests(code, start_line)
        )

    # -----------------------------------------------------
    # 2. ANALYZE INLINE HTML EVENTS
    # -----------------------------------------------------

    for event in parsed_data["inline_events"]:

        all_events.append({

            "event": event["event"][2:],

            "type": "HTML inline",

            "selector": event["element"],

            "line": event["line"] or 1,

            "body": event["code"]

        })

    # -----------------------------------------------------
    # 3. CREATE FUNCTION LOOKUP AND CALL GRAPH
    # -----------------------------------------------------

    function_map = {

        function["name"]: function

        for function in all_functions

    }

    graph = build_call_graph(all_functions)

    # -----------------------------------------------------
    # 4. GENERATE NORMAL REPORT
    # -----------------------------------------------------

    report = generate_report(
        parsed_data,
        analysis_results
    )

    # -----------------------------------------------------
    # 5. FUNCTION DEFINITIONS
    # -----------------------------------------------------

    report += "\n\n5. FUNCTION DEFINITIONS\n"

    for function in all_functions:

        report += (
            f"\nFunction: {function['name']}()\n"
            f"Defined at line: {function['line']}\n"
            f"Parameters: {function['parameters'] or 'None'}\n"
        )

    # -----------------------------------------------------
    # 6. EVENT-TO-FUNCTION FLOW
    # -----------------------------------------------------

    report += "\n\n6. EVENT-TO-FUNCTION FLOW\n"

    if not all_events:

        report += "\nNo supported event handlers found.\n"

    for event in all_events:

        report += (
            f"\nEvent: {event['event']}\n"
            f"Type: {event['type']}\n"
            f"Element: {event['selector']}\n"
            f"Registered at line: {event['line']}\n"
        )

        calls = extract_function_calls(
            event["body"]
        )

        if not calls:

            report += (
                "No direct function calls identified.\n"
            )

        for call in calls:

            name = call["name"]

            report += f"\n  Calls: {name}()\n"

            if name in function_map:

                trace = trace_function(
                    name,
                    function_map,
                    graph
                )

                for item in trace:

                    indent = "    " * (item["depth"] + 1)

                    report += (
                        f"{indent}- {item['message']}\n"
                    )

            else:

                report += (
                    "    - Function definition not found "
                    "in this input file.\n"
                )

    # -----------------------------------------------------
    # 7. BACKEND REQUEST ANALYSIS
    # -----------------------------------------------------

    report += "\n\n7. BACKEND REQUEST ANALYSIS\n"

    if not all_backend_requests:

        report += (
            "\nNo supported AJAX or Fetch requests identified.\n"
        )

    for request in all_backend_requests:

        report += (
            f"\nRequest found at line: {request['line']}\n"
            f"Request type: {request['type']}\n"
            f"Backend endpoint: {request['endpoint']}\n"
            f"HTTP method: {request['method']}\n"
            f"Request data: {request['data']}\n"
            f"Response handling: "
            f"{', '.join(request['response_handling'])}\n"
        )

        if ".php" in request["endpoint"].lower():

            report += (
                "Backend identification: PHP endpoint detected.\n"
            )

    # -----------------------------------------------------
    # 8. PHP BACKEND FILE ANALYSIS
    # -----------------------------------------------------

    report += "\n\n8. PHP BACKEND FILE ANALYSIS\n"

    analyzed_php_files = set()

    for request in all_backend_requests:

        endpoint = request["endpoint"]

        php_path = resolve_php_endpoint(
            endpoint,
            input_path
        )

        if php_path is None:

            report += (
                f"\nEndpoint: {endpoint}\n"
                "PHP file analysis skipped: "
                "Endpoint is dynamic or unsupported.\n"
            )

            continue

        report += (
            f"\nEndpoint: {endpoint}\n"
            f"PHP file path: {php_path}\n"
        )

        # Avoid analyzing the same PHP file repeatedly
        if php_path in analyzed_php_files:

            report += (
                "This PHP file was already analyzed above.\n"
            )

            continue

        analyzed_php_files.add(php_path)

        php_result = analyze_php_file(
            php_path,
            request["data"],
            "\n".join(all_javascript_code)
        )

        if not php_result["exists"]:

            report += (
                "PHP file not found. "
                "Place the endpoint file in the input directory.\n"
            )

            continue

        for message in php_result["messages"]:

            report += f"\n{message}"

        report += "\n"

    # -----------------------------------------------------
    # 9. SAVE REPORT
    # -----------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        report,
        encoding="utf-8"
    )

    print("\nAnalysis completed!")

    print(
        f"Functions identified: {len(all_functions)}"
    )

    print(
        f"Events identified: {len(all_events)}"
    )

    print(
        f"Backend requests identified: "
        f"{len(all_backend_requests)}"
    )

    print(
        f"PHP files inspected: {len(analyzed_php_files)}"
    )

    print(
        f"Report saved to: {output_path}"
    )

    print("\n" + report)


if __name__ == "__main__":
    main()
