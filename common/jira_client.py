from jira import JIRA
import time

class MyJira:
    def __init__(self, jiraserver, username, password):
        self.mLogin_options = {"verify": False}
        self.mJiraServer = jiraserver
        self.mUserName = username
        self.mPassword = password
        self.build_jira()
        self.components_array = set()
        self._field_name_map = None

    def build_jira(self):
        self.mJira = JIRA(self.mJiraServer, options=self.mLogin_options, basic_auth=(self.mUserName, self.mPassword))  # 创建jira连接

    
    def getComments(self, issue_key):
        """
        获取issue的评论内容
        :param issue_key: JIRA issue key
        :return: 评论内容列表
        """
        issue = self._issue_with_retry(issue_key, expand="comments")
        comments = getattr(getattr(issue, "fields", None), "comment", None)
        if not comments or not getattr(comments, "comments", None):
            return []
        return [getattr(comment, "body", "") or "" for comment in comments.comments]

    def getCommentsWithSql(self, sql):
        """
        批量获取多个issue的评论内容
        :param sql: JQL查询语句
        :return: 包含issue key和评论内容列表的结果
        """
        issues = self.search_issues(sql)
        comment_list = []
        for issue in issues:
            comments = self.getComments(issue.key)
            if comments:
                comment_list.append({"key": issue.key, "comments": comments})
        return comment_list

    def getSummary(self, issue_key):
        """
        获取issue的summary
        :param issue_key: JIRA issue key
        :return: summary内容
        """
        issue = self._issue_with_retry(issue_key, expand="summary")
        return getattr(getattr(issue, "fields", None), "summary", None)

    def getSummaryWithSql(self, sql):
        """
        批量获取多个issue的summary
        :param sql: JQL查询语句
        :return: 包含issue key和summary的结果
        """
        issues = self.search_issues(sql)
        summary_list = []
        for issue in issues:
            summary = self.getSummary(issue.key)
            if summary:
                summary_list.append({"key": issue.key, "summary": summary})
        return summary_list

    def getDescription(self, issue_key):
        """
        获取issue的description
        :param issue_key: JIRA issue key
        :return: description内容
        """
        issue = self._issue_with_retry(issue_key, expand="description")
        return getattr(getattr(issue, "fields", None), "description", None)

    def getDescriptionWithSql(self, sql):
        """
        批量获取多个issue的description
        :param sql: JQL查询语句
        :return: 包含issue key和description的结果
        """
        issues = self.search_issues(sql)
        description_list = []
        for issue in issues:
            description = self.getDescription(issue.key)
            if description:
                description_list.append({"key": issue.key, "description": description})
        return description_list
    def getManager(self, issue_key):
        """
        获取issue的manager
        :param issue_key: JIRA issue key
        :return: manager内容
        """
        issue = self._issue_with_retry(issue_key)
        manager = self._get_field_value_by_names(issue, ["manager", "manager id", "manager_id", "窗口人", "窗口经理", "模块经理"])
        return self._pick_user_value(manager)

    def getManagerWithSql(self, sql):
        """
        批量获取多个issue的manager
        :param sql: JQL查询语句
        :return: 包含issue key和manager的结果
        """
        issues = self.search_issues(sql)
        manager_list = []
        for issue in issues:
            manager = self.getManager(issue.key)
            if manager:
                manager_list.append({"key": issue.key, "manager": manager})
        return manager_list

    def getRDSELeader(self, issue_key):
        """
        获取issue的RD/SE Leader
        :param issue_key: JIRA issue key
        :return: RD/SE Leader内容
        """
        issue = self._issue_with_retry(issue_key)
        leader = self._get_field_value_by_names(issue, ["RD/SE Leader", "leader", "owner", "负责人", "窗口负责人", "owner_leader", "assignee"])
        return self._pick_user_value(leader)

    def getRDSELeaderWithSql(self, sql):
        """
        批量获取多个issue的RD/SE Leader
        :param sql: JQL查询语句
        :return: 包含issue key和RD/SE Leader的结果
        """
        issues = self.search_issues(sql)
        leader_list = []
        for issue in issues:
            leader = self.getRDSELeader(issue.key)
            if leader:
                leader_list.append({"key": issue.key, "leader": leader})
        return leader_list
    
    def _get_field_value_by_names(self, issue, names):
        fields = issue.raw.get("fields", {})
        mapping = self._get_field_name_map()
        for name in names:
            field_id = mapping.get(name.lower())
            if field_id and field_id in fields:
                return fields.get(field_id)
        return None

    def _issue_with_retry(self, issue_key, expand=None, max_retries=3, backoff_seconds=1.0):
        last_exc = None
        for attempt in range(1, max_retries + 1):
            try:
                return self.mJira.issue(issue_key, expand=expand) if expand else self.mJira.issue(issue_key)
            except Exception as exc:
                last_exc = exc
                print("jira issue retry {attempt}/{max_retries} failed: {exc}")
                if attempt < max_retries:
                    time.sleep(backoff_seconds * attempt)
        if last_exc:
            raise last_exc
    
    def search_issues(self, jql, maxResults=99999, max_retries=3, backoff_seconds=1.0, page_size=1000):
        """包装JIRA的search_issues方法"""
        target_count = maxResults if isinstance(maxResults, int) and maxResults > 0 else 50
        batch_size = max(1, min(page_size, target_count))
        issues = []
        start_at = 0
        while len(issues) < target_count:
            current_batch_size = min(batch_size, target_count - len(issues))
            last_exc = None
            page = None
            for attempt in range(1, max_retries + 1):
                try:
                    page = self.mJira.search_issues(jql, startAt=start_at, maxResults=current_batch_size)
                    break
                except Exception as exc:
                    last_exc = exc
                    print(f"jira search retry {attempt}/{max_retries} failed: {exc}")
                    if attempt < max_retries:
                        time.sleep(backoff_seconds * attempt)
            if page is None:
                if last_exc:
                    raise last_exc
                break
            page_list = list(page)
            if not page_list:
                break
            issues.extend(page_list)
            if len(page_list) < current_batch_size:
                break
            start_at += len(page_list)
        return issues
    
    def _get_field_name_map(self):
        if self._field_name_map is not None:
            return self._field_name_map
        fields = self.mJira.fields()
        mapping = {}
        for field in fields:
            name = (field.get("name") or "").lower()
            field_id = field.get("id")
            if name and field_id:
                mapping[name] = field_id
        self._field_name_map = mapping
        return mapping

    def _pick_user_value(self, field):
        if isinstance(field, list):
            values = [self._pick_user_value(item) for item in field]
            return ", ".join([v for v in values if v]).strip()
        if isinstance(field, dict):
            return str(field.get("displayName") or field.get("name") or field.get("value") or "").strip()
        if field is None:
            return ""
        display_name = getattr(field, "displayName", None)
        if display_name:
            return str(display_name).strip()
        name = getattr(field, "name", None)
        if name:
            return str(name).strip()
        return str(field).strip()

    def getAiComment(self, issue_key, keyword="AI智能分析"):
        """
        获取issue中第一条包含指定关键字的评论时间
        :param issue_key: JIRA issue key
        :param keyword: 要搜索的关键字，默认为"AI智能分析"
        :return: 第一条匹配评论的创建时间，如果没有匹配则返回None
        """
        issue = self._issue_with_retry(issue_key, expand="comments")
        comments = getattr(getattr(issue, "fields", None), "comment", None)
        if not comments or not getattr(comments, "comments", None):
            return None
        
        for comment in comments.comments:
            body = getattr(comment, "body", "") or ""
            if keyword in body:
                return body
        return None
