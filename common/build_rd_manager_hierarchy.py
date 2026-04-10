import json
from pathlib import Path


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _build_responsibility_map(source_hierarchy_data: dict) -> dict:
    result = {}
    managers = source_hierarchy_data.get("RD Manager") if isinstance(source_hierarchy_data, dict) else []
    if not isinstance(managers, list):
        return result
    for item in managers:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        result[name] = (item.get("responsibility") or "").strip()
    return result


def build_rd_manager_hierarchy(rd_org_data: list[dict], issue_grouped_data: list[dict], responsibility_map: dict | None = None) -> dict:
    responsibility_map = responsibility_map or {}
    issue_map = {}
    component_map = {}
    for item in issue_grouped_data:
        if not isinstance(item, dict):
            continue
        manager = (item.get("RD Manager") or "").strip()
        owner = (item.get("Module Owner") or "").strip()
        if not manager or not owner:
            continue
        issue_map[(manager, owner)] = list(item.get("Issues classification") or [])
        component_map[(manager, owner)] = list(item.get("JIRA Component") or [])

    manager_map = {}
    for item in rd_org_data:
        if not isinstance(item, dict):
            continue
        manager = (item.get("RD Manager") or "").strip()
        module_owner = (item.get("Module Owner") or "").strip()
        jira_owner = (item.get("JIRA default owner") or "").strip()
        if not manager or not module_owner:
            continue

        if manager not in manager_map:
            manager_map[manager] = {
                "name": manager,
                "responsibility": responsibility_map.get(manager, ""),
                "modules": {},
            }

        modules = manager_map[manager]["modules"]
        if module_owner not in modules:
            modules[module_owner] = {
                "module_owner": module_owner,
                "jira_default_owners": [],
                "JIRA Component": component_map.get((manager, module_owner), []),
                "Issues_classification": issue_map.get((manager, module_owner), []),
            }

        if module_owner not in modules[module_owner]["jira_default_owners"]:
            modules[module_owner]["jira_default_owners"].append(module_owner)
        if jira_owner and jira_owner not in modules[module_owner]["jira_default_owners"]:
            modules[module_owner]["jira_default_owners"].append(jira_owner)

    result = {"RD Manager": []}
    for manager_name in sorted(manager_map.keys()):
        manager_item = manager_map[manager_name]
        modules = [manager_item["modules"][key] for key in sorted(manager_item["modules"].keys())]
        result["RD Manager"].append(
            {
                "name": manager_item["name"],
                "responsibility": manager_item["responsibility"],
                "modules": modules,
            }
        )
    return result


def transform_file(rd_org_path: str, issue_grouped_path: str, output_path: str, source_hierarchy_path: str | None = None) -> dict:
    rd_org_data = _load_json(Path(rd_org_path))
    issue_grouped_data = _load_json(Path(issue_grouped_path))
    source_hierarchy_data = _load_json(Path(source_hierarchy_path)) if source_hierarchy_path else {}
    responsibility_map = _build_responsibility_map(source_hierarchy_data)
    result = build_rd_manager_hierarchy(
        rd_org_data if isinstance(rd_org_data, list) else [],
        issue_grouped_data if isinstance(issue_grouped_data, list) else [],
        responsibility_map,
    )
    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    output = transform_file(
        str(base_dir / "rd_orgnization.json"),
        str(base_dir / "jira_issue_manager_owner_grouped.json"),
        str(base_dir / "rd_manager_hierarchy.json"),
        str(base_dir.parent / "rd_manager_hierarchy.json"),
    )
    print(json.dumps(output, ensure_ascii=False, indent=2))
