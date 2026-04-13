"""
CrewAI knowledge_sources 示例
使用 CrewAI 内置 RAG 功能
"""

import os
from crewai import Agent, Task, Crew
from crewai.knowledge import TextFileKnowledgeSource


# 创建知识源
knowledge_source = TextFileKnowledgeSource(
    file_path="./documents/ai_healthcare.txt"
)


# ============ 创建 Agent ============

researcher = Agent(
    role="高级研究员",
    goal="从知识库中准确检索并分析相关信息",
    backstory="你是一位专业的研究员，擅长从海量文档中快速定位关键信息。",
    verbose=True
)

analyst = Agent(
    role="技术分析师",
    goal="基于检索结果提供深入的分析和建议",
    backstory="你是一位经验丰富的技术分析师，能够从复杂信息中提炼出核心观点。",
    verbose=True
)


# ============ 创建 Task ============

research_task = Task(
    description="深入研究以下主题，从知识库中收集相关信息：{topic}",
    expected_output="一份详尽的研究报告，包含关键发现和信息摘要",
    agent=researcher
)

analysis_task = Task(
    description="基于研究结果，提供专业分析和可行建议",
    expected_output="一份结构化的分析报告，包含具体建议",
    agent=analyst,
    context=[research_task]
)


# ============ 创建 Crew（绑定知识源） ============

crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    knowledge_sources=[knowledge_source],  # ← 内置 RAG
    verbose=True,
    # 决定何时让 Agent 使用知识库
    process="sequential"
)


# ============ 运行 ============

if __name__ == "__main__":
    print("=" * 50)
    print("开始研究任务（CrewAI 内置 RAG）...")
    
    topic = "人工智能在医疗领域的应用"
    result = crew.kickoff(inputs={"topic": topic})
    
    print("\n" + "=" * 50)
    print("研究结果:")
    print(result)
