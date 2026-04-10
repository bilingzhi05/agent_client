#枚举类，包含所有信使类型
import enum
class EnvoyType(enum.Enum):
    # 用于查询数据库的信使
    ENVOY_STRATEGISTS = 0
    # 普通信使，用于普通的消息交互
    ENVOY_RAG_SEARCH = 1
    # 用于查询Jira的信使
    ENVOY_LOG_SEARCH = 2
    

prefix_map = {
    "pattern": {
        "prefix": "<|begin_regex_search|>",
        "suffix": "<|end_regex_search|>"
    },
    "log_fetch": {
        "prefix": "<|begin_log_fetch|>",
        "suffix": "<|end_log_fetch|>"
    },
    "reasoning": {
        "prefix": "<|begin_reasoning|>",
        "suffix": "<|end_reasoning|>"
    },
    "tool_call": {
        "prefix": "<|begin_tool_call|>",
        "suffix": "<|end_tool_call|>"
    },
    "max_reasoning_count": {
        "prefix": "<|begin_max_resoning_count|>",
        "suffix": "<|end_max_resoning_count|>"
    },
    "user_command": {
        "prefix": "<|begin_user_command|>",
        "suffix": "<|end_user_command|>"
    },
    "confirmed_facts": {
        "prefix": "<|begin_confirmed_facts|>",
        "suffix": "<|end_confirmed_facts|>"
    },
    "tools_called": {
        "prefix": "<|begin_tools_called|>",
        "suffix": "<|end_tools_called|>"
    },
    "assumption": {
        "prefix": "<|begin_assumption|>",
        "suffix": "<|end_assumption|>"
    },
    "plan": {
        "prefix": "<|begin_plan|>",
        "suffix": "<|end_plan|>"
    },
    "current_analysis_progress": {
        "prefix": "<|begin_current_analysis_progress|>",
        "suffix": "<|end_current_analysis_progress|>"
    }
}
#这是一个结构化的类，用于规范多agent之间的交互结构
class Envoy:   
    TOOL_CALL = "<|tool_call|>"
    ANALYSIS_PROCESS = "<|analysis process|>"
    FINAL_ANSWER = "<|final_answer|>"
    TOOL_CALL_NEW = "<|tool_call|>"
    ANALYSIS_PROCESS_NEW = "<|analysis process|>"
    FINAL_ANSWER_NEW = "<|final_answer|>"
    STEP_EXECUTE = "<|step execute|>"
    #定义成类方法，方便调用
    @classmethod
    def build_pattern_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["pattern"]["prefix"] + "\n" + output + "\n" + prefix_map["pattern"]["suffix"]+"\n"

    @classmethod
    def build_log_fetch_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["log_fetch"]["prefix"] + "\n" + output + "\n" + prefix_map["log_fetch"]["suffix"]+"\n"

    @classmethod
    def build_tool_call_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["tool_call"]["prefix"] + "\n" + output + "\n" + prefix_map["tool_call"]["suffix"]+"\n"
    
    @classmethod
    def build_reasoning_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["reasoning"]["prefix"] + "\n" + output + "\n" + prefix_map["reasoning"]["suffix"]+"\n"
    
    @classmethod
    def build_max_reasoning_count_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["max_reasoning_count"]["prefix"] + "\n" + output + "\n" + prefix_map["max_reasoning_count"]["suffix"]+"\n"
        
    @classmethod
    def build_user_command_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["user_command"]["prefix"] + "\n" + output + "\n" + prefix_map["user_command"]["suffix"]+"\n"
    
    @classmethod
    def build_confirmed_facts_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["confirmed_facts"]["prefix"] + "\n" + output + "\n" + prefix_map["confirmed_facts"]["suffix"]+"\n"
    
    @classmethod
    def build_tools_called_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["tools_called"]["prefix"] + "\n" + output + "\n" + prefix_map["tools_called"]["suffix"]+"\n"
    
    @classmethod
    def build_assumption_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["assumption"]["prefix"] + "\n" + output + "\n" + prefix_map["assumption"]["suffix"]+"\n"
    
    @classmethod
    def build_plan_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["plan"]["prefix"] + "\n" + output + "\n" + prefix_map["plan"]["suffix"]+"\n"
    
    @classmethod
    def build_current_analysis_progress_output_format(cls, output:str)->str:
        #构建输出格式
        return prefix_map["current_analysis_progress"]["prefix"] + "\n" + output + "\n" + prefix_map["current_analysis_progress"]["suffix"]+"\n"

    @classmethod
    def build_step_execute_format(cls, status: str, mode: str, input_ref: str, result: str, facts: list = None) -> str:
        """
        构建 <|step execute|> 的输出格式
        facts 示例: [{'content': '原子事实内容', 'source': '推理/原始数据', 'evidence': '关键证据浓缩或逻辑推导路径'}]
        """
        lines = [
            "<|step execute|>",
            f"- **【执行状态】**: {status}",
            "- **【过程记录】**:",
            f"  1. 执行模式：{mode}",
            f"  2. 输入参照：{input_ref}",
            "- **【执行结果】**:",
            f"  1. {result}",
            "- **【新增事实】**:"
        ]
        
        if not facts:
            lines.append("  无")
        else:
            for i, fact in enumerate(facts, 1):
                content = fact.get('content', '')
                source = fact.get('source', '推理/原始数据')
                evidence = fact.get('evidence', '')
                lines.append(f"  {i}. 新增事实{i}：{content}")
                lines.append(f"     - 依据：[{source}] \"{evidence}\"")
                
        return "\n".join(lines) + "\n"
