# 🧳 智能旅行助手 (Intelligent Travel Assistant)

一个基于 ReAct（Reasoning + Acting）模式的 AI Agent，能够根据用户的自然语言请求，自动查询天气并推荐旅游景点。

## 工作原理

本项目实现了一个简单的 Agent 循环：

1. 用户提出旅行相关请求（如"查询广州天气并推荐景点"）
2. LLM 根据 ReAct 模式进行思考（Thought），决定下一步行动（Action）
3. Agent 解析 Action，调用对应工具获取真实数据（Observation）
4. 将观察结果反馈给 LLM，继续推理，直到任务完成（Finish）

```
用户请求 → LLM 思考 → 调用工具 → 获取结果 → LLM 继续思考 → ... → 输出最终答案
```

## 可用工具

| 工具 | 说明 |
|------|------|
| `get_weather(city)` | 调用 [wttr.in](https://wttr.in) API 查询指定城市的实时天气 |
| `get_attraction(city, weather)` | 调用 [Tavily Search API](https://tavily.com) 根据城市和天气推荐旅游景点 |

## 环境要求

- Python 3.10+
- 兼容 OpenAI 接口的 LLM 服务

## 安装

```bash
pip install requests openai tavily-python
```

## 配置

在项目根目录创建 `.env` 文件，配置以下环境变量：

```env
# LLM 服务配置（任何兼容 OpenAI 接口的服务均可）
OPENAI_API_KEY="your-api-key"
OPENAI_API_BASE="https://api.example.com/v1"
MODEL_ID="your-model-id"

# Tavily 搜索 API 密钥（用于景点推荐）
TAVILY_API_KEY="your-tavily-api-key"
```

> Tavily API Key 可在 [tavily.com](https://tavily.com) 免费申请。

## 运行

```bash
python intelligent_travel_assistant/IntelligentTravelAssistantAgent.py
```

默认会执行一个示例请求：查询广州天气并推荐景点。如需修改查询内容，编辑代码中的 `user_prompt` 变量即可。

## 示例输出

```
用户输入: 你好，请帮我查询一下今天广州的天气，然后根据天气推荐一个合适的旅游景点。
========================================
--- 循环 1 ---
正在调用大语言模型...
模型输出:
Thought: 用户想知道广州的天气，我先调用天气查询工具。
Action: get_weather(city="广州")

Observation: 广州当前天气：Sunny，气温32摄氏度
========================================
--- 循环 2 ---
正在调用大语言模型...
模型输出:
Thought: 已获取天气信息，接下来根据天气推荐景点。
Action: get_attraction(city="广州", weather="Sunny，气温32摄氏度")

Observation: 推荐景点...
========================================
--- 循环 3 ---
任务完成，最终答案: ...
```

## 项目结构

```
intelligent_travel_assistant/
├── IntelligentTravelAssistantAgent.py  # Agent 主程序（包含工具定义、LLM 客户端、主循环）
└── README.md                           # 本文件
```

## 技术栈

- [OpenAI Python SDK](https://github.com/openai/openai-python) — LLM 调用
- [Tavily Python SDK](https://github.com/tavily-ai/tavily-python) — 搜索引擎 API
- [wttr.in](https://github.com/chubin/wttr.in) — 天气查询 API
