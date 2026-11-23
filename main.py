
from pathlib import Path

from parser import extract_javascript
from analyzer import analyze_javascript
from explainer import generate_report


INPUT_FILE = "input/sample.html"
OUTPUT_FILE = "output/flow_report.txt"


def main():

    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_FILE)

    if not input_path.exists():
        print("Input file not found!")
        return

    print("Starting JavaScript Flow Analyzer...")

    # Step 1: Parse HTML/PHP
    parsed_data = extract_javascript(input_path)

    # Step 2: Analyze internal scripts
    analysis_results = []

    for script in parsed_data["scripts"]:

        results = analyze_javascript(
            script["code"],
            script["line"]
        )

        analysis_results.extend(results)

    # Step 3: Analyze inline event handlers
    for event in parsed_data["inline_events"]:

        results = analyze_javascript(
            event["code"],
            event["line"] or 1
        )

        analysis_results.extend(results)

    # Step 4: Generate report
    report = generate_report(
        parsed_data,
        analysis_results
    )

    # Step 5: Save report
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_path.write_text(
        report,
        encoding="utf-8"
    )

    print("\nAnalysis completed!")
    print(f"Report saved to: {output_path}")

    print("\n" + report)


if __name__ == "__main__":
    main()
