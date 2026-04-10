# from utils.jira_client import MyJira
# from utils.llm_client import build_llm_client
# from config import (jira_config , llm_presets)
from common.config import ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG
from agents.SimpleAgent import SimpleAgent
from common.utils import fetch_json_content, print_log_with_box
import re
import json
import csv
import time
# import requests
from typing import Dict, Tuple

import re
import urllib3
from common.jira_client import MyJira

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# from enum import Enum
# class ModelType(Enum):
#     MODEL_TYPE_OPENAI = "openai"
#     MODEL_TYPE_OLLAMA = "ollama"
#     MODEL_TYPE_DASHSCOPE = "dashscope"
# ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG = {
#   "model_type": ModelType.MODEL_TYPE_OPENAI,
#   "args":{
#       "id": "DeepSeek-V3-2",
#       "temperature": 0.2,
#       "top_p": 0.8,
#       "seed": 42,
#       "frequency_penalty": 0.1,
#       "api_key":"138091f2-9072-4a68-b0fc-3caf862ddf01",
#       "max_tokens": 131702,
#       "max_completion_tokens": 65535,
#       "base_url": "https://llm.amlogic.com/8d1b5b4c"
#   }
# }





# llm_client = build_llm_client(config=llm_presets["ollama_qwen3_8b"])
# prompt_text = llm_client._build_prompt("你是谁？", "")
user_prompt = """
IPTV
"""


def extract_jira_id(text):
    match = re.search(r"\b[A-Z][A-Z0-9]+-\d+\b", text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(0).upper()

jira_module_recognize_instructions = '''
你是一个**模块问题归属判断专家**。你的任务是根据提供的模块人员信息和 Jira 问题描述，判断该问题初步属于哪个窗口人负责。

Jira 信息介绍：
1. Jira 信息包含summary和description, 以及AI智能分析评论
2. 从summary和description，中判断该问题可能由哪一个模块引起的，如果有AI智能分析评论，也需要综合AI智能分析评论判断。 

职责 信息介绍：
1. **manager**：必须从人员信息 JSON 的一级 key 中选择最匹配的人。
2. **owner**：必须从该 manager 的 `owner_team` 中选择一个最相关的人。
3. **人员信息规则**：以下 JSON 是实际人员数据，不是示例；一级 key 为 manager，`manager_responsibilities` 是职责说明，`owner_team` 的 key 是可选 owner 列表，必须严格从中选择。

匹配规则：
1. 问题可能的模块名称，必须与职责信息中的 `manager_responsibilities` 匹配。
2. 如果问题可能的模块名称，与职责信息中的 `manager_responsibilities` 匹配失败，需要根据 `owner_team` 中的 key 匹配。
3. 禁止根据文件名判断模块归属，只能根据 Jira 信息介绍中的summary和description，以及AI智能分析评论判断。
3. 输出结果必须是 JSON 格式，开头使用 ```json，结尾使用 ```。
4. JSON 示例：
```json
{
    "manager": "Guofeng Tang",
    "owner": "guoping.Li",
    "reason": "问题可能的模块名称，以及原因说明"
}
只能根据提供的模块人员信息来判断，不要猜测其他人员。

不要输出任何额外文字，纯 JSON 格式。

下面是模块人员信息（JSON 结构）：
{
  "Ashok Patil": {
    "manager_responsibilities": "Zapper App 应用管理",
    "owner_team": {
      "Karan Singh": "Zapper App 应用工作"
    }
  },
  "Frank Chen": {
    "manager_responsibilities": "Fuchsia 平台管理",
    "owner_team": {
      "Frank.Chen": "Fuchsia 系统/内核",
      "Manliang Tang": "Fuchsia 用户态驱动"
    }
  },
  "Guofeng Tang": {
    "manager_responsibilities": "统筹多产品形态下的 Linux framework 架构与交付，覆盖 RDK YouTube、TV/OTT、SmartHome、IPC 及 RDK Feature 等系统框架方向，同时负责 Video Encoder 用户接口与算法能力在各平台中的集成与稳定性保障。",
    "owner_team": {
      "Guofeng Tang": "RDK-Youtube 与 TV/OTT Linux framework",
      "Guoping Li": "SmartHome Linux framework",
      "Jun Zhang": "Yocto TV/OTT Linux framework",
      "Xuequan Feng": "IPC Linux framework",
      "Yang Liu": "Video Encoder 用户接口与算法",
      "Zhengyu Gao": "RDK Feature Linux framework"
    }
  },
  "Jian Xu": {
    "manager_responsibilities": "音频系统管理 (DSP/dobly/AQ/Driver/Framework/Decoder/Platform/IPTV)",
    "owner_team": {
      "Jian Xu": "Audio-platform 与 IPTV 音频问题",
      "Shuai Li": "DSP/Audio 驱动与平台音频",
      "Wei Du": "Audio-decoder 与 Linux/RDK 平台",
      "Yang Liu": "HiFi DSP 音频",
      "Yujie Wu": "Framework / Decoder 音频播放, Dolby相关",
      "Zhe Wang": "Audio-AQ 音效与 TV 音频"
    }
  },
  "Jerry Cao": {
    "manager_responsibilities": "Architecture-System 管理",
    "owner_team": {
      "Jerry Cao": "Architecture-System 模块"
    }
  },
  "Pradeep Sriram": {
    "manager_responsibilities": "RDK SDK 与 RDK Residence App 管理",
    "owner_team": {
      "Pradeep Sriram": "RDK SDK 与 Residence App 问题"
    }
  },
  "Simon Zheng": {
    "manager_responsibilities": "统筹显示与多媒体相关模块的研发与交付，覆盖视频显示与HDR链路、CVBS/Vchip/Teletext等模拟信号兼容、PQ画质调校、Graphics与HDMI接口输出、Camera影像采集，以及NN DDK与算法在端侧多媒体场景中的落地与稳定性保障。",
    "owner_team": {
      "Brian Zhu": "HDR / Video 显示",
      "Lei Yang": "CVBS / Vchip/Teletext",
      "Mingliang Dong": "PQ 画质",
      "Sky Zhou": "Graphics / HDMI",
      "Xiaoxin Cao": "Camera",
      "Jinhong Zhang": "NN DDK",
      "Xingwei Zhou": "NN Algorithm"
    }
  },
  "Tao Dong": {
    "manager_responsibilities": "统筹 Android TV/OTT 系统整体架构与交付，涵盖 BSP 与系统稳定性、TV/OTT 多媒体应用与云游戏、系统工具链与升级能力、显示系统与画质调校、数字电视制式协议栈，以及视频输入与 DTV Demod 等关键模块的集成与稳定性保障。",
    "owner_team": {
      "Sandy Luo": "BSP / 系统稳定性",
      "Shen Liu": "TV 应用层与多媒体应用",
      "Wenbiao Zhang": "OTT 应用与云游戏",
      "Yihui Wu": "系统工具链与升级",
      "Zhe Huang": "显示系统与PQ tuning/server",
      "Lei Qian": "数字电视制式协议栈",
      "Nengwen Chen": "视频输入与 DTV Demod"
    }
  },
  "Tellen Yu": {
    "manager_responsibilities": "统筹 Android 系统在 TV 与 Vehicle 场景下的基础框架与构建能力、多媒体底层支持、自动化与认证测试体系、TV Input/Broadcast 能力、Google 设备维护、车载系统适配，以及系统网络类问题的定位与稳定性保障。",
    "owner_team": {
      "Shuide Chen": "系统框架 / Build / 多媒体基础能力",
      "Haisha Ning": "自动化平台",
      "Liang Ji": "认证与测试体系",
      "Kieth Liu": "TV Input / Broadcast",
      "Songqiang Lu": "Google 设备维护",
      "Yongzhi Gao": "车载系统",
      "Jia Wen": "系统网络问题"
    }
  },
  "Terrence Pu": {
    "manager_responsibilities": "RDK 第三方应用与 Amazon 平台",
    "owner_team": {
      "Terrence Pu": "第三方应用集成与 Amazon 支持"
    }
  },
  "Tim Yao": {
    "manager_responsibilities": "多媒体系统架构与 Netflix 集成",
    "owner_team": {
      "Tim Yao": "多媒体架构与 Netflix RDK 支持"
    }
  },
  "Victor Wan": {
    "manager_responsibilities": "统筹系统底层软件能力建设与交付，覆盖 Bootloader 与 Secure Boot 安全启动链路、Linux Kernel 性能与安全优化、CPU 与 DSP 底层架构能力、各类外设与高速/无线(wifi/bt)/Broadcast/存储驱动、电源与功耗管理、Bootloader 工具链，以及 Secure OS/TEE/CAS 与 RTOS 内核等关键基础模块的集成与稳定性保障。",
    "owner_team": {
      "Jianxin Pan": "Linux Kernel 性能与安全",
      "Tao Zeng": "Bootloader 与 Secure Boot",
      "Bo Lv": "Bootloader 平台能力",
      "Xia Jin": "CPU 架构与底层能力",
      "Zhongfu Luo": "Bootloader 工具链",
      "Peifu Jiang": "Secure OS / TEE / System TA / CAS 系统",
      "Ke Gong": "Broadcast Driver",
      "Yonghui Yu": "Peripheral / Storage Driver",
      "Qi Duan": "高速接口驱动",
      "Rongjun Chen": "无线(wifi/bt)驱动",
      "Qiufang Dai": "电源与功耗管理，DSP 内核架构",
      "Kelvin Zhang": "RTOS 内核"
    }
  },
  "Zhi Zhou": {
    "manager_responsibilities": "统筹 Android/Linux 媒体播放全链路能力建设与交付，涵盖媒体网络栈、播放器核心框架、Media Framework 与 Codec 能力、视频解码器、DRM/CAS 安全体系，以及平台认证相关工作的集成与稳定性保障。",
    "owner_team": {
      "Lifeng Cao": "播放器核心框架",
      "Peng Wu": "Media Framework / Codec / 平台认证",
      "Tao Guo": "DRM / CAS 系统",
      "Hui Zhang": "视频解码器",
      "Bo Xiao": "Linux Media / 播放器",
      "Kejun Gao": "媒体网络栈"
    }
  },
  "Zhiheng Cao": {
    "manager_responsibilities": "IPTV 播放器框架与运营商定制",
    "owner_team": {
      "Chuanqi Wang": "IPTV AmPlayer",
      "Jiwei Sun": "运营商播放器"
    }
  },
  "Lei Li": {
    "manager_responsibilities": "全球数字电视协议栈与频道系统",
    "owner_team": {
      "Hujian Zheng": "DTV 核心功能",
      "Bin Lu": "DTV 扫描与前端",
      "Bing Feng": "DTV 高层业务"
    }
  }
}

'''

def get_rd_owner_with_jira_info(summary: str = "") -> dict:
    result = {"RD_owner": ""}
    try:
        if not summary:
            return result
        agent = SimpleAgent(model_args=ANALYZER_OPENAI_DEEPSEEK_V3_CONFIG, prompt=jira_module_recognize_instructions)
        response = agent.run(content=summary)
        print_log_with_box(f"\nagent.run(content = summary) response:{response}")
        tmp_value = fetch_json_content(response)
        if tmp_value:
            result["RD_owner"] = tmp_value.get("owner", "")
            result["RD_manager"] = tmp_value.get("manager", "")
            result["RD_reason"] = tmp_value.get("reason", "")
            print_log_with_box(f"\n该问题的对应RD是{result}")
        else:
            print_log_with_box("\n获取RD窗口人的信息失败。。。。\n")
    except Exception as e:
        print_log_with_box(f"获取RD窗口人的信息失败。。。。{e}")
    return result



# 从模型输出中提取 JSON
def _extract_json(text):
    m = re.search(r"```json\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    payload = m.group(1) if m else text
    try:
        return json.loads(payload)
    except Exception:
        try:
            payload = payload[payload.find("{"): payload.rfind("}") + 1]
            return json.loads(payload)
        except Exception:
            return {}

# 获取 Jira 信息并生成归属结果
def recognize_manager_owner(jira_id, comments = ""):
    output = {
        "jira_id": "",
        "agent_manager": "",
        "agent_owner": "",
        "jira_manager": "",
        "jira_owner": "",
        "correct_manager": None,
        "summary": "",
        "description": "",
        "RD_reason": "",
    }
    if comments:
        output["comments"] = jira_client.getAiComment(jira_id, comments)
        comments = output["comments"]
    if not jira_id:
        return output

    summary = jira_client.getSummary(jira_id) or ""
    if "]" in summary:
        summary = summary.split("]")[-1].strip()
    description = jira_client.getDescription(jira_id) or ""
    prompt = f"""
    问题JIRA：{jira_id}
    summary：
    {summary}

    description：
    {description}
    """
    if comments:
        prompt += f"""
        AI智能分析：
        {comments}
        """
    print(f"comments:{comments}\n\nprompt:{prompt}")
    # system_prompt = jira_module_recognize_instructions
    # res = llm_client.qa_with_system(system_prompt=system_prompt, user_prompt=prompt)
    res = get_rd_owner_with_jira_info(prompt)
    print_log_with_box(f"\nget_rd_owner_with_jira_info(prompt) response:{res}")
    rd_owner = res.get("RD_owner", "")
    rd_manager = res.get("RD_manager", "")
    rd_reason = res.get("RD_reason", "")

    print(f"rd_owner:{rd_owner}")
    # res_json = _extract_json(res) or {}

    jira_manager = jira_client.getManager(jira_id) or ""
    jira_owner = jira_client.getRDSELeader(jira_id) or ""
    output["jira_id"] = jira_id
    output["summary"] = summary
    output["description"] = description
    output["agent_manager"] = rd_manager
    output["agent_owner"] = rd_owner
    output["jira_manager"] = jira_manager
    output["jira_owner"] = jira_owner
    output["correct_manager"] = rd_manager == jira_manager
    output["correct_owner"] = rd_owner == jira_owner
    output["RD_reason"] = rd_reason
    return output

jira_client = MyJira("https://jira.amlogic.com", "lingzhi.bi", "Qwer!23456")
# jql = "project = \"OTT projects\" AND labels = se-a and createdDate >= 2022-1-1"
# jql = "project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC"

jql = "key = OTT-93228	"
issues = jira_client.search_issues(jql)
len_issues = len(issues)
writer = None
file_handle = open(f"rd_owner_result_aicomments_{len_issues}.csv", "w", encoding="utf-8", newline="")
for issue in issues:
    jira_id = issue.key
    # result = recognize_manager_owner(jira_id,"AI智能分析")
    result = recognize_manager_owner(jira_id)
    print(f"output:{result}")
#     if writer is None:
#         writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
#         writer.writeheader()
#     writer.writerow(result)
#     file_handle.flush()
# file_handle.close()

jqls = []
jqls.append("project = \"OTT projects\" and priority in (High,Highest) and type = Bug and createdDate >= 2025-12-25 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC") 
jqls.append("project = \"OTT projects\" AND text ~ AI智能分析 and Manager not in (zh.cao,shawn.wu) ORDER BY created DESC")
# jqls.append("key = OTT-93228")

# for jql in jqls:
#   issues = jira_client.search_issues(jql)
#   len_issues = len(issues)
#   writer = None
#   file_handle = open(f"rd_owner_result_{len_issues}.csv", "w", encoding="utf-8", newline="")
#   for issue in issues:
#       jira_id = issue.key
#       # result = recognize_manager_owner(jira_id,"AI智能分析")
#       result = recognize_manager_owner(jira_id)
#       print(f"output:{result}")
#       if writer is None:
#           writer = csv.DictWriter(file_handle, fieldnames=list(result.keys()))
#           writer.writeheader()
#       writer.writerow(result)
#       file_handle.flush()
#   file_handle.close()


# summary = '[TiVo][Kaon][S905X4][Android S][ZAP-1850] Video freezes or displays a loading icon when the Multiview option is selected'
# rd_owner_info = get_rd_owner_with_jira_info(summary)
# print(f"rd_owner_info:{rd_owner_info}")
