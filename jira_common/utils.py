from common.config import JIRA_PASSWORD, JIRA_SERVER, JIRA_USERNAME
from common.jira_client import MyJira
import re


_jira_client = None


def _get_jira_client():
    global _jira_client
    if _jira_client is None:
        _jira_client = MyJira(JIRA_SERVER, JIRA_USERNAME, JIRA_PASSWORD)
    return _jira_client


def get_jira_info(jira_id):
    jira_client = _get_jira_client()
    summary = jira_client.getSummary(jira_id) or ""
    summary = re.sub(r"\[[^\[\]]*\]|【[^【】]*】", "", summary)
    summary = re.sub(r"\s{2,}", " ", summary).strip()

    description = jira_client.getDescription(jira_id) or ""
    agent_comment = jira_client.getAiComment(jira_id) or ""
    comments = jira_client.getComments(jira_id) or []
    jira_manager = jira_client.getManager(jira_id) or ""
    jira_owner = jira_client.getRDSELeader(jira_id) or ""
    return {
        "jira_id": jira_id,
        "summary": summary,
        "description": description,
        "agent_comment": agent_comment,
        "comments": comments,
        "jira_manager": jira_manager,
        "jira_owner": jira_owner,
    }


def get_jira_manager_history(jira_id):
    jira_client = _get_jira_client()

    def _norm_field_name(name):
        return re.sub(r"[\s_]+", "", str(name or "")).strip().lower()

    def _add_manager(managers, seen, name):
        name = str(name or "").strip()
        if not name:
            return
        if name in seen:
            return
        seen.add(name)
        managers.append(name)

    manager_field_names = [
        "manager",
        "manager id",
        "manager_id",
        "窗口人",
        "窗口经理",
        "模块经理",
    ]
    manager_fields = {_norm_field_name(n) for n in manager_field_names}

    managers = []
    seen = set()
    _add_manager(managers, seen, jira_client.getManager(jira_id))

    try:
        issue = jira_client._issue_with_retry(jira_id, expand="changelog")
    except Exception:
        return managers

    changelog = getattr(issue, "changelog", None)
    histories = getattr(changelog, "histories", None) or []
    for history in histories:
        items = getattr(history, "items", None) or []
        for item in items:
            field = _norm_field_name(getattr(item, "field", ""))
            if field not in manager_fields:
                continue
            _add_manager(managers, seen, getattr(item, "fromString", None))
            _add_manager(managers, seen, getattr(item, "toString", None))

    return managers

managers = get_jira_manager_history("OTT-94894")
print(f"managers: {managers}")