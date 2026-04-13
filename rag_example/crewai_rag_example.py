"""
CrewAI RAG 示例
基于 CrewAI 框架的检索增强生成应用
"""

import os
from crewai import Agent, Task, Crew
from crewai.tools import tool
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.retrievers import TFIDFRetriever
from langchain_core.documents import Document


# ============ RAG 工具定义 ============

_retriever = None


def get_retriever():
    """获取 TF-IDF 检索器"""
    global _retriever
    if _retriever is not None:
        return _retriever
    
    data_path = "./documents"
    if not os.path.exists(data_path):
        return None
    
    loader = DirectoryLoader(data_path, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    if not documents:
        return None
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    texts = text_splitter.split_documents(documents)
    
    _retriever = TFIDFRetriever.from_documents(texts)
    return _retriever


@tool("retrieve_docs")
def retrieve_docs(query: str) -> str:
    """从知识库中检索与查询相关的文档内容"""
    retriever = get_retriever()
    if retriever is None:
        return "未找到相关文档，请先添加文档到 documents 目录"
    
    docs = retriever.invoke(query)
    if not docs:
        return "未找到相关文档"
    
    context = "\n\n".join([f"文档 {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)])
    return context


@tool("rag_qa")
def rag_qa(query: str) -> str:
    """基于检索增强的问答工具"""
    docs = retrieve_docs(query)
    return f"【RAG 增强回答】\n\n检索到的相关内容:\n{docs}\n\n基于以上内容，可以回答您的问题。"


# ============ RAG 验证测试 ============

def test_rag():
    """测试 RAG 检索功能"""
    print("=" * 50)
    print("RAG 检索功能测试")
    print("=" * 50)
    
    retriever = get_retriever()
    if retriever is None:
        print("❌ 知识库为空或 documents 目录不存在")
        return False
    
    # 测试查询
    test_queries = [
        "AI在医疗影像诊断中的应用",
        "药物研发AI技术",
        "精准医疗"
    ]
    
    print(f"✓ 知识库已加载\n")
    
    for query in test_queries:
        print(f"查询: {query}")
        docs = retriever.invoke(query)
        print(f"  → 检索到 {len(docs)} 条相关结果")
        if docs:
            print(f"  → 内容预览: {docs[0].page_content[:80]}...")
        print()
    
    print("=" * 50)
    print("✅ RAG 检索功能正常")
    return True


# ============ CrewAI Agent 和 Task ============

def create_research_crew() -> Crew:
    """创建研究团队"""
    
    researcher = Agent(
        role="高级研究员",
        goal="从知识库中准确检索并分析相关信息",
        backstory="你是一位专业的研究员，擅长从海量文档中快速定位关键信息。",
        tools=[retrieve_docs],
        verbose=True
    )
    
    analyst = Agent(
        role="技术分析师",
        goal="基于检索结果提供深入的分析和建议",
        backstory="你是一位经验丰富的技术分析师，能够从复杂信息中提炼出核心观点。",
        tools=[rag_qa],
        verbose=True
    )
    
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
    
    crew = Crew(
        agents=[researcher, analyst],
        tasks=[research_task, analysis_task],
        verbose=True
    )
    
    return crew


def main():
    """主函数"""
    
    # 先测试 RAG
    if not test_rag():
        return
    
    print("\n" + "=" * 50)
    print("创建 CrewAI 研究团队...")
    crew = create_research_crew()
    
    print("=" * 50)
    print("开始研究任务...")
    
    topic = "人工智能在医疗领域的应用"
    result = crew.kickoff(inputs={"topic": topic})
    
    print("\n" + "=" * 50)
    print("研究结果:")
    print(result)


if __name__ == "__main__":
    main()
