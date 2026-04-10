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
   
