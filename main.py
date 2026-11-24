from pathlib import Path
from backend_analyzer import detect_backend_requests
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


INPUT_FILE =  "input/v5_test2_fetch_post.html"
OUTPUT_FILE = "output/flow_report.txt"


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

    # Analyze internal script blocks
    for script in parsed_data["scripts"]:

        code = script["code"]
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

    # Analyze inline HTML event handlers
    for event in parsed_data["inline_events"]:

        all_events.append({
            "event": event["event"][2:],
            "type": "HTML inline",
            "selector": event["element"],
            "line": event["line"] or 1,
            "body": event["code"]
        })

    # Create function lookup and call graph
    function_map = {
        function["name"]: function
        for function in all_functions
    }

    graph = build_call_graph(all_functions)

    # Generate normal report
    report = generate_report(
        parsed_data,
        analysis_results
    )

    # Add function definitions
    report += "\n\n5. FUNCTION DEFINITIONS\n"

    for function in all_functions:

        report += (
            f"\nFunction: {function['name']}()\n"
            f"Defined at line: {function['line']}\n"
            f"Parameters: {function['parameters'] or 'None'}\n"
        )

    # Add event execution flow
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

        calls = extract_function_calls(event["body"])

        if not calls:
            report += "No direct function calls identified.\n"

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

    report += "\n\n7. BACKEND REQUEST ANALYSIS\n"

    if not all_backend_requests:
        report += "\nNo supported AJAX or Fetch requests identified.\n"

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

    # Save report
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        report,
        encoding="utf-8"
    )

    print("\nAnalysis completed!")
    print(f"Functions identified: {len(all_functions)}")
    print(f"Events identified: {len(all_events)}")
    print(f"Report saved to: {output_path}")

    print("\n" + report)


if __name__ == "__main__":
    main()