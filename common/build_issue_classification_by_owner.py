import json
from pathlib import Path


def build_issue_classification_by_owner(data: list[dict]) -> list[dict]:
    grouped = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        rd_manager = (item.get("RD Manager") or "").strip()
        module_owner = (item.get("Module Owner") or "").strip()
        jira_component = (item.get("JIRA Component") or "").strip()
        issue_classification = (item.get("Issues classification") or "").strip()
        if not rd_manager or not module_owner:
            continue
        key = (rd_manager, module_owner)
        if key not in grouped:
            grouped[key] = {
                "RD Manager": rd_manager,
                "Module Owner": module_owner,
                "JIRA Component": [],
                "Issues classification": [],
            }
        if jira_component and jira_component not in grouped[key]["JIRA Component"]:
            grouped[key]["JIRA Component"].append(jira_component)
        if issue_classification and issue_classification not in grouped[key]["Issues classification"]:
            grouped[key]["Issues classification"].append(issue_classification)
    return list(grouped.values())


def transform_file(input_file: str, output_file: str) -> list[dict]:
    source_path = Path(input_file)
    target_path = Path(output_file)
    data = json.loads(source_path.read_text(encoding="utf-8"))
    result = build_issue_classification_by_owner(data if isinstance(data, list) else [])
    target_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_path = base_dir / "jira_issue_manager_owner.json"
    output_path = base_dir / "jira_issue_manager_owner_grouped.json"
    grouped = transform_file(str(input_path), str(output_path))
    print(json.dumps(grouped, ensure_ascii=False, indent=2))
