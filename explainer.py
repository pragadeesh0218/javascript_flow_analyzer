
def generate_report(parsed_data, analysis_results):

    report = []

    report.append("=" * 60)
    report.append("JAVASCRIPT FLOW ANALYSIS REPORT")
    report.append("=" * 60)

    report.append("\n1. JAVASCRIPT EXECUTION ANALYSIS\n")

    if not analysis_results:
        report.append("No recognized JavaScript patterns found.")

    for item in analysis_results:

        report.append(
            f"Line {item['line']}: {item['explanation']}"
        )

        report.append(
            f"Code: {item['code']}\n"
        )

    report.append("\n2. INLINE EVENT HANDLERS\n")

    for event in parsed_data["inline_events"]:

        report.append(
            f"Line {event['line']}: "
            f"{event['element']} element triggers "
            f"{event['event']} event."
        )

        report.append(f"Code: {event['code']}\n")

    report.append("\n3. EXTERNAL JAVASCRIPT FILES\n")

    for script in parsed_data["external_scripts"]:

        report.append(
            f"Line {script['line']}: "
            f"External JavaScript file: {script['src']}"
        )

    report.append("\n4. OVERALL SUMMARY\n")

    report.append(
        f"Found {len(parsed_data['scripts'])} internal script blocks."
    )

    report.append(
        f"Found {len(parsed_data['inline_events'])} inline event handlers."
    )

    report.append(
        f"Found {len(parsed_data['external_scripts'])} external JS references."
    )

    report.append(
        f"Generated {len(analysis_results)} code explanations."
    )

    return "\n".join(report)
