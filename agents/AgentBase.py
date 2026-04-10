from typing import Union
from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.models.dashscope import DashScope
from agno.models.openai import OpenAILike
from sqlalchemy import union
from logger.Logger import get_logger
from common.utils import remove_think_content,print_log_with_box
from agno.media import Audio, File, Image, Video
from common.config import ModelType
class AgentBase:
    def __init__(self, name: str = "assistant", role: str = "assistant", model_args: dict = None,  with_format_output: bool = True, instructions: Union[list[str], str] = None, output_json: bool = False):
        self.name = name
        self.role = role
        self.logger = get_logger(self.name)
        self.with_format_output = with_format_output
        self.model_type = model_args["model_type"]
        self.model_args = model_args["args"]
        self.model = None
        self.output_json = output_json
        if self.model_type == ModelType.MODEL_TYPE_OLLAMA:
            self.model = Ollama(**self.model_args)
        elif self.model_type == ModelType.MODEL_TYPE_DASHSCOPE:
            self.model = DashScope(**self.model_args)
        elif self.model_type == ModelType.MODEL_TYPE_OPENAI:
            self.model = OpenAILike(**self.model_args)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")
        if self.output_json:
            self.agent = Agent(
                name=name,
                role=role,
                model=self.model,
                instructions= instructions,
                use_json_mode=True,
                structured_outputs=True
            )
        else:
            self.agent = Agent(
                name=name,
                role=role,
                model=self.model,
                instructions= instructions
            )
    def format_output(self, input:str="None", format_function:callable=None):
        output = input
        if self.with_format_output:
            if format_function:
                output = format_function(input)
        return output

    def run(self, content : str = None, images: list[Image] = None, stream: bool = True, stream_intermediate_steps: bool = True, debug_mode: bool = False)->str:
        output = ""
        if content is None or content.strip() == "":
            return "error: content为空"
        print("\n==============开始请求大模型===============\n")
        for event in self.agent.run(input = f"{content}", images=images, stream=stream, stream_intermediate_steps=stream_intermediate_steps, debug_mode = debug_mode):
            if event.event == 'RunStarted':
                print("\n=============================\n")
                print_log_with_box(f"\n{self.name}分析开始...\n\n", self.logger, log_level="debug")
            elif event.event == 'ToolCallStarted':
                print_log_with_box("\n工具调用开始...\n\n", self.logger, log_level="debug")
            elif event.event == 'ToolCallCompleted':
                print_log_with_box("\n工具调用完成...\n\n", self.logger, log_level="debug")
            elif event.event == 'RunContent':
                print(event.content, end='', flush=True)
                output += event.content
            elif event.event == 'RunCompleted':
                print("\n=============================\n")
                break
            else:
                print(event)
                break
        print("\n==============请求大模型结束===============\n")
        output = remove_think_content(output)
        return self.format_output(output)

    def run_yield(self, content : str = None, images: list[Image] = None, stream: bool = True, stream_intermediate_steps: bool = True, debug_mode: bool = False)->str:
        output = ""
        if content is None or content.strip() == "":
            return "error: content为空"

        for event in self.agent.run(input = f"{content}", images=images, stream=stream, stream_intermediate_steps=stream_intermediate_steps, debug_mode = debug_mode):
            if event.event == 'RunStarted':
                print("\n=============================\n")
                print_log_with_box(f"\n{self.name}分析开始...\n\n", self.logger, log_level="debug")
            elif event.event == 'ToolCallStarted':
                print_log_with_box("\n工具调用开始...\n\n", self.logger, log_level="debug")
            elif event.event == 'ToolCallCompleted':
                print_log_with_box("\n工具调用完成...\n\n", self.logger, log_level="debug")
            elif event.event == 'RunContent':
                print(event.content, end='', flush=True)
                yield event.content
            elif event.event == 'RunCompleted':
                print("\n=============================\n")
                break