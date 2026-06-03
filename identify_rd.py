import json
import re
from pathlib import Path
import urllib3
from logger.logger import log as mylog
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jira_macro_identify_instructions = '''
# Role
你是一个**高精度分类判定 Agent（Deterministic Classifier）**。
你的唯一任务是：基于输入内容与候选类型列表，通过“溯源排查法”选择**最匹配的唯一类型**。

---

# Input
输入包含两部分：
1. **待分类内容**
2. **类型列表（带判定依据）**：
   每个类型包含：index、类型名称、判定依据。

---

# Core Principles

1. **唯一性原则（强制）**
   - 必须且只能选择一个类型。
   - 严禁输出多个候选或不确定结论。

2. **业务溯源优先原则（关键）**
   - **逻辑嵌套判定**：若问题表现为 A 类型（如网络报错），但明确是在执行 B 类型（如支付、下单）的操作流程中触发的，必须判定为 **B 类型**。
   - **排查顺序**：先判定“操作归属/诱因”，再判定“末端表现”。
   - **边界规则**：对于跨模块问题，优先分配给“发起该操作的业务方”进行第一轮排查。

3. **依据优先原则**
   - 分类必须严格基于“判定依据”，禁止使用常识扩展。

4. **最匹配原则**
   - 多个候选命中时，选择“业务逻辑深度更深”或“流程覆盖度最高”的类型。

5. **禁止过度推理**
   - 不得补充输入中不存在的信息，不得进行假设性判断。

6. 禁止跳步骤（极其重要）
   - 在完成“候选池筛选”前，禁止进行最终类型判断
   - 必须严格执行下方 Decision Process
---

# Decision Process（必须严格执行，属于内部思维步骤）

你必须分两阶段完成判定：

【阶段一：候选池筛选】
- 逐个检查所有类型的“判定依据”
- 只要判定依据与输入内容有明确匹配，即加入候选池
- 本阶段允许多个候选类型，严禁在此阶段做最终选择

【阶段二：候选池唯一化】
仅在候选池中执行以下优先级淘汰规则：

优先级1：
若候选池中包含以下类型名称之一：
Simon Zheng / Tellen Yu / Jian Xu / Zhi Zhou
必须只在这几个类型中选择

优先级2：
否则，若包含以下类型名称之一：
Tao Dong / Victor Wan
必须只在这几个类型中选择

优先级3：
否则，才在剩余候选中选择“业务溯源最深”的类型

【最终】
从候选池中选出唯一类型输出

---

# Format Rules（格式强校验规则）

1. **标题必须完全一致**：必须为 `## 分类结果`。
2. **字段顺序固定**：必须按 `index` -> `type` -> `reason` 顺序排列。
3. **字段名称固定**：只能使用 `index`, `type`, `reason`。
4. **分隔符固定**：必须使用 `- 空格 key: 空格 value`（例如：`- index: 1`）。
5. **换行规则**：标题下一行必须直接是 `- index`，每个字段独占一行，总行数必须为 4 行。
6. **禁止额外内容**：禁止输出分析过程、代码块、解释或多余标点。

---

# Output Format（严格遵守）

## 分类结果
- index: <类型下标>
- type: <类型名称>
- reason: <1-2句简要原因(包含类型名称选择原因)，必须体现为何根据操作上下文进行溯源判定>

---

# Example

**Input:**
内容：用户在进行“实名认证”上传身份证照片时，界面提示“连接服务器超时，请重试”。
类型列表：
0: 网络连接问题（判定依据：超时、404、断网、连接失败）
1: 账户安全/实名（判定依据：实名认证、证件上传、账号申诉）

**Output:**

## 分类结果
- index: 1
- type: 账户安全/实名
- reason: 虽表现为网络超时，但发生在实名认证特定流程中，根据溯源原则应由该业务模块优先排查全链路问题。

'''

def _load_macro_map_data() -> dict:
        map_path = Path(__file__).resolve().parent / "jira_macro_type_map_v2.json"
        with map_path.open("r", encoding="utf-8") as f:
            return json.load(f)

def _extract_type_by_index(result_text: str, candidates: list[dict]) -> str:
    normalized = (result_text or "").strip()

    # First, parse the new required markdown format from jira_owner_identify_instructions.
    markdown_pattern = (
        r"##\s*分类结果\s*\n"
        r"- index:\s*(\d+)\s*\n"
        r"- type:\s*(.+?)\s*\n"
        r"- reason:\s*(.+)"
    )
    reason = ""
    markdown_match = re.search(markdown_pattern, normalized, re.DOTALL)
    if markdown_match:
        index = int(markdown_match.group(1))
        selected_type = markdown_match.group(2).strip()
        reason = markdown_match.group(3).strip()
        if 0 <= index < len(candidates):
            return (candidates[index].get("name") or "").strip() ,reason
        if selected_type:
            for item in candidates:
                if (item.get("name") or "").strip() == selected_type:
                    return selected_type, reason
    return "",reason

def _build_macro_candidates(macro_data: dict) -> list[dict]:
    candidates = []
    for item in macro_data.get("macro_categories", []):
        candidates.append(
            {
                "name": (item.get("macro_type") or "").strip(),
                "basis": "；".join(item.get("classification_hints", [])),
            }
        )
    return [it for it in candidates if it["name"]]


def _build_user_input(content: str, candidates: list[dict]) -> str:
    lines = [f"{idx}: {item['name']}（判定依据：{item['basis']}）" for idx, item in enumerate(candidates)]
    return (
        f"待分类内容：{content}\n"
        "类型列表：\n"
        + "\n".join(lines)
    )

def _extract_english_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        return ""
    matched = re.match(r"([A-Za-z]+(?:\s+[A-Za-z]+)*)", normalized)
    if matched:
        return matched.group(1).strip()
    return normalized


def identify_jira_manager(jira_id: str, summary: str, description: str, ai_comments: str = "") -> tuple[str, str]:
    from agents.SimpleAgent import SimpleAgent
    from common.config import ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG, ANALYZER_DASHSCOPE_DEEPSEEK_V3_CONFIG

    if ai_comments:
        content = f"jira信息：summary:{summary}\n, description:{description}\n, 初步分析：{ai_comments}\n"
    else:
        content = f"jira信息：summary:{summary}\n, description:{description}\n"

    macro_map_data = _load_macro_map_data()
    macro_candidates = _build_macro_candidates(macro_map_data)
    round1_input = _build_user_input(content, macro_candidates)
    mylog(f"identify_jira_manager jira_id:{jira_id}, round1_input:{round1_input}")

    round1_agent = SimpleAgent(
        model_args=ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG,
        prompt=jira_macro_identify_instructions,
        output_json=False,
    )
    round1_result = round1_agent.run(content=round1_input)
    mylog(f"identify_jira_manager jira_id:{jira_id}, round1_result:{round1_result}")

    macro_type, macro_reason = _extract_type_by_index(round1_result, macro_candidates)
    manager = _extract_english_name(macro_type)
    mylog(f"identify_jira_manager jira_id:{jira_id}, macro_type:{macro_type}, manager:{manager}")
    return manager, macro_reason



def identify_rd(jira_key: str = "OTT-93265", with_comments: bool = True) -> dict:

    from jira_common.utils import get_jira_info, get_jira_manager_history
    output = {
        "jira_id": "",
        "agent_manager": "",
        "agent_manager_reason": "",
        "jira_manager": "",
        "correct_manager": None,
        "summary": "",
        "description": "",
        "ai_comments": "",
    }
    collection_info = get_jira_info(jira_id=jira_key)
    output["jira_id"] = jira_key
    output["summary"] = collection_info.get("summary")
    output["description"] = collection_info.get("description")
    output["jira_manager"] = collection_info.get("jira_manager", "")
    ai_comments = collection_info.get("agent_comment", "")

    if ai_comments:
        output["ai_comments"] = ai_comments
    macro_map_data = _load_macro_map_data()

    manager, relevant_reasons = identify_jira_manager(
        jira_id=jira_key,
        summary=collection_info.get("summary", ""),
        description=collection_info.get("description", ""),
        ai_comments=ai_comments
    )
    output["agent_manager"] = manager
    output["agent_manager_reason"] = relevant_reasons
    output["correct_manager"] = output["jira_manager"] == output["agent_manager"]
    if output["correct_manager"] is False:
        agent_manager = (output.get("agent_manager") or "").strip()
        if agent_manager:
            history_managers = get_jira_manager_history(output.get("jira_id") or jira_key)
            if agent_manager.lower() in {str(m or "").strip().lower() for m in history_managers}:
                output["correct_manager"] = "H_True"

    mylog(f"output:{output}")
    return output


if __name__ == "__main__":
    # final_result, output = identify_rd(jira_key="OTT-93202")
    # mylog(json.dumps(final_result, ensure_ascii=False, indent=2))
    from common.jira_client import MyJira
    import csv
    from datetime import datetime
    jqls = []
    jira_client = MyJira("https://jira.amlogic.com", "lingzhi.bi", "Qwer!23456")
    # jql = "project = \"OTT projects\" AND labels = se-a and createdDate >= 2022-1-1"
    # jql = "project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC"
    # jql = "project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) and createdDate >= 2026-3-1 and createdDate <= 2026-3-5 order BY created DESC"
    # jqls.append("project = \"OTT projects\" and priority in (High,Highest) and type = Bug and createdDate >= 2025-12-25 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC") 
    # jqls.append("project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) and createdDate >= 2026-3-26 and createdDate <= 2026-3-28 order BY created DESC")
    # jqls.append("key = OTT-93227")

    # jqls.append("""key in (
    #     OTT-93520, OTT-93515, OTT-93458, OTT-93430, OTT-93402,
    #     OTT-93339, OTT-93295, OTT-93290, OTT-93270, OTT-93265,
    #     OTT-93263, OTT-93262, OTT-93260, OTT-93257, OTT-93252,
    #     OTT-93248, OTT-93247, OTT-93245, OTT-93240, OTT-93239,
    #     OTT-93238, OTT-93236, OTT-93235, OTT-93228, OTT-93227,
    #     OTT-93224, OTT-93223, OTT-93222, OTT-93205, OTT-93202
    #     )""") 
    # timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # for jql in jqls:
    #     issues = jira_client.search_issues(jql)
    #     len_issues = len(issues)
    #     writer = None
    #     file_handle = open(f"rd_owner_result_{len_issues}_{timestamp}.csv", "w", encoding="utf-8", newline="")
    #     for issue in issues:
    #         jira_id = issue.key
    #         _,result = identify_rd(jira_id, with_comments=False)
    #         # mylog(f"output:{result}")
    #         if writer is None:
    #             writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
    #             writer.writeheader()
    #         writer.writerow(result)
    #         file_handle.flush()
    #     file_handle.close()
    
    # jql = "project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) and createdDate >= 2026-3-26 and createdDate <= 2026-3-28 order BY created DESC"
    jql = "text ~ AI智能分析 AND priority in (High,Highest) and Manager not in (zh.cao, shawn.wu) AND createdDate >= 2026-2-2 ORDER BY priority DESC, created DESC"
    # jql = """key in (
    #     OTT-93520, OTT-93515, OTT-93458, OTT-93430, OTT-93402,
    #     OTT-93339, OTT-93295, OTT-93290, OTT-93270, OTT-93265,
    #     OTT-93263, OTT-93262, OTT-93260, OTT-93257, OTT-93252,
    #     OTT-93248, OTT-93247, OTT-93245, OTT-93240, OTT-93239,
    #     OTT-93238, OTT-93236, OTT-93235, OTT-93228, OTT-93227,
    #     OTT-93224, OTT-93223, OTT-93222, OTT-93205, OTT-93202
    #     )"""
    issues = jira_client.search_issues(jql)
    len_issues = len(issues)
    writer = None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_handle = open(f"rd_owner_result_aicomments_{len_issues}_{timestamp}.csv", "w", encoding="utf-8", newline="")
    for issue in issues:
        jira_id = issue.key
        # result = recognize_manager_owner(jira_id,"AI智能分析")
        result = identify_rd(jira_id, with_comments=True)
        # mylog(f"output:{result}")
        if writer is None:
            writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
            writer.writeheader()
        writer.writerow(result)
        file_handle.flush()
    file_handle.close()

