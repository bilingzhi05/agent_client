
from common.config import ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG, ANALYZER_DASHSCOPE_DEEPSEEK_V3_CONFIG
from jira_common.utils import get_jira_info
from common.utils import fetch_json_content
import json
import re
from pathlib import Path
import urllib3
from logger.logger import log as mylog
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

jira_owner_identify_instructions = '''
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

---

# Decision Process（内部执行，不输出）

1. **提取核心特征**：识别“故障表现”与“操作上下文（触发动作）”。
2. **执行顺序排查**：
   - 检查是否存在明确的业务操作背景？
   - 该操作对应的类型判定依据是否能覆盖此场景？（优先选业务方）。
3. **匹配判定依据**：对比剩余类型的关键词。
4. **确定唯一结果**：选择最优 index，并根据溯源逻辑撰写原因。

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
- reason: <1-2句简要原因，必须体现为何根据操作上下文进行溯源判定>

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

2. **类型名称选择方法**
   - 先看是否是这三个类型名称中的问题（Simon Zheng，Tellen Yu，Jian Xu，Zhi Zhou）
   - 如果不是，再看是否是这两个类型名称的问题（Tao Dong，Victor Wan）。
   - 如果不是，最后再看看是否是剩下类型名称的问题。

3. **业务溯源优先原则（关键）**
   - **逻辑嵌套判定**：若问题表现为 A 类型（如网络报错），但明确是在执行 B 类型（如支付、下单）的操作流程中触发的，必须判定为 **B 类型**。
   - **排查顺序**：先判定“操作归属/诱因”，再判定“末端表现”。
   - **边界规则**：对于跨模块问题，优先分配给“发起该操作的业务方”进行第一轮排查。

4. **依据优先原则**
   - 分类必须严格基于“判定依据”，禁止使用常识扩展。

5. **最匹配原则**
   - 多个候选命中时，选择“业务逻辑深度更深”或“流程覆盖度最高”的类型。

6. **禁止过度推理**
   - 不得补充输入中不存在的信息，不得进行假设性判断。

---

# Decision Process（内部执行，不输出）

1. **提取核心特征**：识别“故障表现”与“操作上下文（触发动作）”。
2. **执行顺序排查**：
   - 检查是否存在明确的业务操作背景？
   - 该操作对应的类型判定依据是否能覆盖此场景？（优先选业务方）。
3. **匹配判定依据**：对比剩余类型的关键词。
4. **确定唯一结果**：选择最优 index，并根据溯源逻辑撰写原因。

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

jira_identify_more_macro_instructions = '''
# Role
你是一个**高精度分类判定 Agent（Deterministic Classifier）**。
你的唯一任务是：基于输入内容与候选类型列表，**选择出最匹配的几个类型**。

---
# Core Principles
1. **基本规则**
   - 分类必须严格基于“判定依据”，禁止使用常识扩展。
   - 选择的类型按照相关度排序，相关度最高的排在最前面。
2. **类型名称选择方法**
   - 先看是否是这三个类型名称中的问题（Simon Zheng，Tellen Yu，Jian Xu，Zhi Zhou）
   - 如果不是，再看是否是这两个类型名称的问题（Tao Dong，Victor Wan）。
   - 如果不是，最后再看看是否是剩下类型名称的问题。

---
# Input
输入包含两部分：
1. **待分类内容**
2. **类型列表（带判定依据）**：
   每个类型包含：index、类型名称、判定依据。

---

# Output Format（严格遵守）
```json
{
  "select_types": [
    {
      "index": <类型下标>,
      "type": "<类型名称>",
      "reason": "<1-2句简要原因(包含类型名称选择原因)，必须体现为何根据操作上下文进行溯源判定>"
    }
  ],
  "relevant_reasons": "<总结上述类型选择相关度的顺序原因>"
}
```
'''
def _load_macro_map_data() -> dict:
        map_path = Path(__file__).resolve().parent / "jira_macro_type_map.json"
        with map_path.open("r", encoding="utf-8") as f:
            return json.load(f)

def _extract_type_by_index(result_text: str, candidates: list[dict], fallback_text: str = "") -> str:
    normalized = (result_text or "").strip()

    # First, parse the new required markdown format from jira_owner_identify_instructions.
    markdown_pattern = (
        r"##\s*分类结果\s*\n"
        r"- index:\s*(\d+)\s*\n"
        r"- type:\s*(.+?)\s*\n"
        r"- reason:\s*(.+)"
    )
    markdown_match = re.search(markdown_pattern, normalized, re.DOTALL)
    if markdown_match:
        index = int(markdown_match.group(1))
        selected_type = markdown_match.group(2).strip()
        if 0 <= index < len(candidates):
            return (candidates[index].get("name") or "").strip()
        if selected_type:
            for item in candidates:
                if (item.get("name") or "").strip() == selected_type:
                    return selected_type

    # Fallback: keep json parsing for compatibility with old model outputs.
    parsed = fetch_json_content(normalized)
    if isinstance(parsed, dict):
        index = parsed.get("index")
        if isinstance(index, int) and 0 <= index < len(candidates):
            return (candidates[index].get("name") or "").strip()
        selected_type = (parsed.get("type") or "").strip()
        if selected_type:
            for item in candidates:
                if (item.get("name") or "").strip() == selected_type:
                    return selected_type
    for item in candidates:
        name = (item.get("name") or "").strip()
        if name and name in fallback_text:
            return name
    return ""

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

def _build_owner_candidates(selected_macro: dict) -> list[dict]:
    candidates = []
    for comp in selected_macro.get("components", []):
        owner = (comp.get("owner") or "").strip()
        basis = (comp.get("issues_classification") or "").strip()
        component = (comp.get("component") or "").strip()
        if owner:
            candidates.append(
                {
                    "name": owner,
                    "basis": f"component={component}; 判定依据={basis}",
                }
            )
    return candidates

def _build_user_input(content: str, candidates: list[dict]) -> str:
    lines = [f"{idx}: {item['name']}（判定依据：{item['basis']}）" for idx, item in enumerate(candidates)]
    return (
        f"待分类内容：{content}\n"
        "类型列表：\n"
        + "\n".join(lines)
    )

def _extract_priority_type_by_index(result_text: str, candidates: list[dict]) -> str:
    normalized = (result_text or "").strip()
    parsed = fetch_json_content(normalized)
    if not isinstance(parsed, dict):
        return ""
    select_types = parsed.get("select_types")
    relevant_reasons = parsed.get("relevant_reasons")
    if not isinstance(select_types, list) or not select_types:
        return ""

    selected_names = []
    for item in select_types:
        if isinstance(item, dict):
            index = item.get("index")
            if isinstance(index, int) and 0 <= index < len(candidates):
                name = (candidates[index].get("name") or "").strip()
                if name:
                    selected_names.append(name)
                    continue
            type_name = (item.get("type") or "").strip()
            if type_name:
                selected_names.append(type_name)

    if not selected_names:
        return ""

    mylog(f"selected_names:{selected_names}")
    first_priority = ["Simon Zheng", "Tellen Yu", "Jian Xu", "Zhi Zhou"]
    second_priority = ["Tao Dong", "Victor Wan"]

    for name in selected_names:
        for first_priority_name in first_priority:
            if first_priority_name in name:
                return name, relevant_reasons
    for name in selected_names:
        for second_priority_name in second_priority:
            if second_priority_name in name:
                return name, relevant_reasons
    return selected_names[0], relevant_reasons


def _extract_english_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        return ""
    matched = re.match(r"([A-Za-z]+(?:\s+[A-Za-z]+)*)", normalized)
    if matched:
        return matched.group(1).strip()
    return normalized

def identify_rd(jira_key: str = "OTT-93265", with_comments: bool = True) -> dict:
    from agents.SimpleImpAgent import SimpleImpAgent
    from agents.SimpleAgent import SimpleAgent
    output = {
        "jira_id": "",
        "agent_manager": "",
        "agent_manager_reason": "",
        "agent_owner": "",
        "agent_owner_reason": "",
        "jira_manager": "",
        "jira_owner": "",
        "correct_manager": None,
        "correct_owner": None,
        "summary": "",
        "description": "",
        "ai_comments": "",
    }
    collection_info = get_jira_info(jira_id=jira_key)
    output["jira_id"] = jira_key
    output["summary"] = collection_info.get("summary")
    output["description"] = collection_info.get("description")
    output["jira_manager"] = collection_info.get("jira_manager", "")
    output["jira_owner"] = collection_info.get("jira_owner", "")
    # if not collection_info.get("files", []):
    #     mylog(f"{jira_key} 未包含附件，跳过...")
    #     raise Exception(f"{jira_key} 未包含附件，跳过...")
    
    if with_comments:
        content = f"jira信息：summary:{collection_info.get('summary')}\n, description:{collection_info.get('description')}\n, 初步分析：{collection_info.get('agent_comment', '')}\n"
        output["ai_comments"] = collection_info.get("agent_comment", "")
    else:
        content = f"jira信息：summary:{collection_info.get('summary')}\n, description:{collection_info.get('description')}\n"
    macro_map_data = _load_macro_map_data()

    macro_candidates = _build_macro_candidates(macro_map_data)
    round1_input = _build_user_input(content, macro_candidates)
    # round1_input += "\n**模块责任人选择方法：**\n先看是否是这三位中的问题（Simon Zheng，Tellen Yu，Jian Xu，Zhi Zhou）\n"
    # round1_input += "如果不是，再看是否是这二位的问题（Tao Dong，Victor Wan）。\n"
    # round1_input += "如果不是，最后再看看是否是剩下人的问题。\n"
    mylog(f"round1_input:{round1_input}")
    # round1_agent = SimpleImpAgent(
    round1_agent = SimpleAgent(
        model_args=ANALYZER_DASHSCOPE_DEEPSEEK_V3_CONFIG,
        prompt=jira_identify_more_macro_instructions,
        # prompt=jira_macro_identify_instructions,
        output_json=False,
    )
    round1_result = round1_agent.run(content=round1_input)
    mylog(f"round1_result:{round1_result}")
    macro_type, relevant_reasons = _extract_priority_type_by_index(round1_result,macro_candidates)
    # macro_type = _extract_type_by_index(round1_result, macro_candidates, round1_result)
    mylog(f"macro_type:{macro_type}")
    manager = macro_type
    output["agent_manager"] = _extract_english_name(manager)
    output["agent_manager_reason"] = relevant_reasons
    # Round 2: classify owner under the selected macro type.
    selected_macro = None
    for item in macro_map_data.get("macro_categories", []):
        if (item.get("macro_type") or "").strip() == macro_type:
            selected_macro = item
            break

    owner_candidates = _build_owner_candidates(selected_macro or {})
    round2_input = _build_user_input(content, owner_candidates)
    mylog(f"round2_input:{round2_input}")
    # round2_agent = SimpleImpAgent(
    round2_agent = SimpleAgent(
        model_args=ANALYZER_DASHSCOPE_DEEPSEEK_V3_CONFIG,
        prompt=jira_owner_identify_instructions,
        output_json=False,
    )
    round2_result = round2_agent.run(content=round2_input)
    owner = _extract_type_by_index(round2_result, owner_candidates, round2_result)
    output["agent_owner"] = _extract_english_name(owner)
    output["agent_owner_reason"] = round2_result
    output["correct_manager"] = output["jira_manager"] == output["agent_manager"]
    output["correct_owner"] = output["jira_owner"] == output["agent_owner"]
    final_result = {
        "content": content,
        "manager": manager or macro_type or "unknown",
        "macro_type": macro_type or "unknown",
        "owner": owner or "unknown",
        "round1_raw": round1_result,
        "round2_raw": round2_result,
    }
    return final_result, output


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
    jqls.append("project = \"OTT projects\" and priority in (High,Highest) and type = Bug and createdDate >= 2025-12-25 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC") 
    jqls.append("project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) and createdDate >= 2026-3-26 and createdDate <= 2026-3-28 order BY created DESC")
    # jqls.append("key = OTT-93202")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for jql in jqls:
        issues = jira_client.search_issues(jql)
        len_issues = len(issues)
        writer = None
        file_handle = open(f"rd_owner_result_aicomments_{len_issues}_{timestamp}.csv", "w", encoding="utf-8", newline="")
        for issue in issues:
            jira_id = issue.key
            _,result = identify_rd(jira_id, with_comments=False)
            mylog(f"output:{result}")
            if writer is None:
                writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
                writer.writeheader()
            writer.writerow(result)
            file_handle.flush()
        file_handle.close()
    
    jql = "project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) and createdDate >= 2026-3-26 and createdDate <= 2026-3-28 order BY created DESC"
    issues = jira_client.search_issues(jql)
    len_issues = len(issues)
    writer = None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_handle = open(f"rd_owner_result_aicomments_{len_issues}_{timestamp}.csv", "w", encoding="utf-8", newline="")
    for issue in issues:
        jira_id = issue.key
        # result = recognize_manager_owner(jira_id,"AI智能分析")
        _,result = identify_rd(jira_id, with_comments=True)
        mylog(f"output:{result}")
        if writer is None:
            writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
            writer.writeheader()
        writer.writerow(result)
        file_handle.flush()
    file_handle.close()

