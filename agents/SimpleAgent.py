from operator import truediv
from time import strftime
from agents.AgentBase import AgentBase
from agno.tools import tool
from common.config import (
    ANALYZER_OLLAMA_MODEL_CONFIG,
    SUMMARY_OLLAMA_MODEL_CONFIG,
    LLM_MAX_CHAR_LENGTH,
    VL_OLLAMA_MODEL_CONFIG,
    LLM_CONTEXT_CONTEXT_MAX_CHAR_LENGTH,
    log_analyzer_collection_info_instruction,
    log_analyzer_direct_instruction,
    log_analyzer_summary_instruction,
    jira_status_analyze_instructions,
    log_classify_instructions,
    jira_classify_common_instructions,
    cts_gts_picture_recognition_instruction
)
# from protocol.Envoy import Envoy
import os
from common.utils import remove_think_content,print_log_with_box,fetch_json_content,truncate_content
# from jira_common.utils import handle_jira_data
from agno.media import Image
from common.config import ModelType
class SimpleAgent(AgentBase):

    def __init__(self, model_args:dict= {}, prompt: [list[str], str] = None, use_think_content: bool = True, with_format_output: bool = True, vl_model: bool = False, output_json: bool = True):
        #检查提示词是否为空
        if prompt is None or prompt.strip() == "":
            prompt = "你是一个智能助手，回答用户的问题"
        model_args_target = {}
        if not model_args :
            if not vl_model:
                model_args_target = ANALYZER_OLLAMA_MODEL_CONFIG if use_think_content else SUMMARY_OLLAMA_MODEL_CONFIG
            else:
                model_args_target = VL_OLLAMA_MODEL_CONFIG
        else:
            model_args_target = model_args
        super().__init__(
            name="SimpleAgent",
            role="SimpleAgent",
            model_args= model_args_target,
            instructions= prompt,
            output_json = output_json,
            with_format_output = with_format_output
        )
    # def __init__(self, model_args:dict= {}, prompt: [list[str], str] = None, with_format_output: bool = True):
    #     #检查提示词是否为空
    #     if prompt is None or prompt.strip() == "":
    #         prompt = "你是一个智能助手，回答用户的问题"
    #     model_args_target = model_args
    #     super().__init__(
    #         name="SimpleAgent",
    #         role="SimpleAgent",
    #         model_args= model_args_target,
    #         instructions= prompt,
    #         with_format_output = with_format_output
    #     )

    # def format_output(self, input:str="None"):
    #     if self.with_format_output:
    #         return super().format_output(input, Envoy.build_reasoning_output_format)
    #     else:
    #         return input

    #提取不超过固定字符的内容的函数
    def extract_content(self, content: list[str] = None, start_index: int = 0, max_length: int = LLM_MAX_CHAR_LENGTH):
        """
        以 content 数组中的每一个字符串为单位，不切割单个字符串，
        只取总长度不超过 max_length 的字符串，并返回下一次开始的索引和提取出来的字符串。
        """
        if content is None:
            return "", 0
        # 从 start_index 开始遍历
        selected_lines = []
        current_length = 0
        next_index = start_index

        for idx in range(start_index, len(content)):
            line = content[idx]
            line_len = len(line)
            # 如果加上这一行会超过最大长度，则停止
            if current_length + line_len > max_length:
                break
            selected_lines.append(line)
            current_length += line_len
            next_index = idx + 1

        extracted = "".join(selected_lines)
        return extracted, next_index

    #写一个函数，分段总结日志分析结果
    def run_with_chunks(self, context: str = "", chunks : list[str] = None, images: list[Image] = None, debug_mode: bool = False):
        #检查context和logs是否正常
        if context is None:
            return "error: context或logs为空"
        context = context.strip()
        if context == "":
            return "error: context为空"

        single_content_flag = False
        if len(chunks) == 0:
            single_content_flag = True
            print("error: logs为空")
        else:
            more_content = [chunk for chunk in chunks if chunk != ""]
            if len(more_content) == 0:
                single_content_flag = True
                print("error: logs为空")
        final_context = ""
        summary = ""
        #context上下不要超context的LLM_CONTEXT_CONTEXT_MAX_CHAR_LENGTH最大上限
        if not chunks:
            context = truncate_content(context, LLM_MAX_CHAR_LENGTH)
        else:
            context = truncate_content(context, LLM_CONTEXT_CONTEXT_MAX_CHAR_LENGTH)
        # 提取不超过最大字符长度的内容
        if single_content_flag:
            summary = self.run(content=f"信息如下：\n {context} ", images=images, debug_mode=debug_mode)
        else:
            next_index = 0
            count = 0
            while next_index < len(more_content):
                content, next_index = self.extract_content(more_content, next_index)
                summary = self.run(content=f"基本信息如下：\n {context} \n 补充信息如下：\n{content}", images=images, debug_mode=debug_mode)
                final_context += summary
                final_context += "\n"
                count += 1
            if count > 1:
                summary = self.run(content=f"基本信息如下：\n {context} \n 补充信息如下：\n{final_context}", images=images, debug_mode=debug_mode)
        return summary

if __name__ == "__main__":
    from pprint import pprint
    agent = SimpleAgent(prompt = cts_gts_picture_recognition_instruction, use_think_content=True, with_format_output=False, vl_model=True)
    # agent = SimpleAgent("你是一个可以识别图片内容的智能助手，按照用户要求提取图片信息", use_think_content=True, with_format_output=False, vl_model=True)
    #提取logs内容到数组中
    # jira_content = "接上U盘，launcer不能弹出通知，检查u盘是否挂载成功，若成功则检查是否有广播意图或通知服务调用"
    # target_jiras = [
    #     "OTT-88352",
    #     "OTT-88246",
    #     "OTT-88076",
    #     "OTT-87864",
    #     "OTT-87766",
    #     "OTT-87679",
    #     "OTT-87644",
    #     "OTT-87614",
    #     "OTT-87604",
    #     "OTT-87492",
    #     "OTT-87463",
    #     "OTT-87434",
    #     "OTT-87376",
    #     "OTT-87322",
    #     "OTT-87319",
    #     "OTT-87318",
    #     "OTT-87317",
    #     "OTT-87316",
    #     "OTT-87314",
    #     "OTT-87279",
    #     "OTT-87223",
    #     "OTT-87222",
    #     "OTT-87153",
    #     "OTT-87117",
    #     "OTT-87076",
    #     "OTT-86974",
    #     "OTT-86949",
    #     "OTT-86940",
    #     "OTT-86852",
    #     "OTT-86850"
    # ]
    # target_jiras = ["OTT-86850"]
    # class_map = dict()
    # for key in target_jiras:
    #     result = handle_jira_data(key, [], with_files_download=False)
    #     files = result["files"]
    #     content = result["content"]
    #     description = result["description"]
    #     comments = result["comments"]
    #     project = result["project"]
    #     sdk_version = result["sdk_version"]
    #     print(project)
    #     print(sdk_version)
    #     result = ""
    #     print_log_with_box(f"开始分析jira {key}")
    #     response = agent.run_with_chunks(context = f"jira summary: {content}\n description: {description}\n", chunks = comments)
    #     print_log_with_box(f"分析jira {key}的结果如下：\n{response}")
    #     class_map[key] = response
    # print_log_with_box(class_map)
    response = agent.run_with_chunks(context = f"提取cts/gts测试结果中的失败项的结构化信息", chunks = [], images = [Image(filepath ="./tmp/CtsMediaTestCases.png")])
    # response = agent.run_with_chunks(context = f"提取图片中的文字信息", chunks = [], images = [Image(filepath ="./tmp/cts_failed2.png")])
    print_log_with_box(f"结果如下：\n{response}")
    # json_result = fetch_json_content(response)
    # #剔除掉files里与json_result中irrelevant_files_or_logs字段中相同的项
    # files = [file for file in files if file not in json_result["irrelevant_files_or_logs"]]
    # final_data = dict()
    # final_data["reproduction_steps"] = json_result["reproduction_steps"]
    # final_data["analysis_direction"] = json_result["analysis_direction"]
    # final_data["suspicious_logs"] = json_result["suspicious_logs"]
    # final_data["irrelevant_files_or_logs"] = json_result["irrelevant_files_or_logs"]
    # final_data["is_certification_related"] = json_result["is_certification_related"]
    # final_data["main_user_pain_point"] = json_result["main_user_pain_point"]
    # final_data["one_sentence_summary"] = json_result["one_sentence_summary"]
    # final_data["summary"] = content
    # final_data["description"] = description
    # final_data["comments"] = comments
    # final_data["files"] = files
    # final_data["project"] = project
    # final_data["sdk_version"] = sdk_version

    # pprint(final_data)
