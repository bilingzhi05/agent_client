import json
from pathlib import Path


def build_rd_organization(data: list[dict]) -> list[dict]:
    grouped = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        manager = (item.get("RD Manager") or "").strip()
        module_owner = (item.get("Module Owner") or "").strip()
        jira_owner = (item.get("JIRA default owner") or "").strip()
        key = (manager, module_owner)
        if key not in grouped:
            grouped[key] = {
                "RD Manager": manager,
                "Module Owner": module_owner,
                "JIRA default owner": [],
            }
            if module_owner:
                grouped[key]["JIRA default owner"].append(module_owner)
        if jira_owner and jira_owner not in grouped[key]["JIRA default owner"]:
            grouped[key]["JIRA default owner"].append(jira_owner)
    return list(grouped.values())


def transform_file(input_path: str, output_path: str) -> list[dict]:
    source = Path(input_path)
    target = Path(output_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    result = build_rd_organization(data if isinstance(data, list) else [])
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    input_file = base_dir / "rd_orgnization.json"
    output_file = base_dir / "rd_orgnization_grouped.json"
    transformed = transform_file(str(input_file), str(output_file))
    print(json.dumps(transformed, ensure_ascii=False, indent=2))
