import yaml
from pathlib import Path
from pocketflow import AsyncNode, AsyncParallelBatchNode
from utils.code_utils import discover_code_files, extract_code_units
from utils.async_call_llm import call_llm
from utils.knowledge_graph import initialize_index, add_to_index, get_knowledge_graph_data_for_saving


class DiscoverProjectNode(AsyncNode):
    """
    Scans the repository path to find all relevant source files and determine
    the project's language and testing framework.
    """
    async def exec_async(self, prep_res):
        repo_path = self.params.get("repo_path")
        if not repo_path:
            raise ValueError("repo_path must be provided in flow params")
        
        print(f"Discovering code files in {repo_path}...")
        source_files = discover_code_files(repo_path)
        
        language = "Python"
        test_framework = "pytest"
        
        return {
            "source_files": source_files,
            "language": language,
            "test_framework": test_framework
        }

    async def post_async(self, shared, prep_res, exec_res):
        shared["project_analysis"] = exec_res
        print(f"Discovered {len(exec_res['source_files'])} source files. Language: {exec_res['language']}.")


class GenerateSummariesNode(AsyncParallelBatchNode):
    """
    Takes a list of source files and generates a natural language summary
    for each "code unit" (e.g., function, class) within them. This runs in parallel
    for maximum speed.
    """
    concurrency = 5

    async def prep_async(self, shared):
        source_files = shared["project_analysis"]["source_files"]
        
        # --- FIX: Filter out __init__.py files from being summarized ---
        files_to_summarize = [f for f in source_files if not f.endswith('__init__.py')]
        
        all_units = []
        for file_path in files_to_summarize:
            all_units.extend(extract_code_units(file_path))
            
        print(f"Found {len(all_units)} code units to summarize (excluding __init__.py files).")
        print(f"Running summarization with a concurrency limit of {self.concurrency} to avoid rate limiting.")
        return all_units

    async def exec_async(self, code_unit):
        prompt = f"""
Analyze the following code unit from the file '{code_unit['file_path']}'.
Unit Name: {code_unit['unit_name']}

Code:

IGNORE_WHEN_COPYING_START
Use code with caution. Python
IGNORE_WHEN_COPYING_END

{code_unit['code']}
Generated code

Your task is to provide a concise, natural language summary that includes:
1. The primary purpose of the code unit.
2. A brief description of its parameters (if any).
3. A brief description of its return value (if any).
4. A list of other functions or methods it calls internally.
"""
        summary = await call_llm(prompt, use_cache=True)
        code_unit['summary'] = summary
        return code_unit

    async def post_async(self, shared, prep_res, exec_res_list):
        successful_summaries = [res for res in exec_res_list if isinstance(res, dict) and 'summary' in res]
        shared["code_summaries"] = successful_summaries
        print(f"Generated summaries for {len(successful_summaries)} out of {len(exec_res_list)} code units.")


class BuildKnowledgeGraphNode(AsyncParallelBatchNode):
    """
    Embeds all generated code summaries and adds them to the knowledge graph (vector database).
    """
    concurrency = 10
    
    async def prep_async(self, shared):
        embedding_dim = 1024
        initialize_index(dimension=embedding_dim)
        print(f"Building knowledge graph with a concurrency limit of {self.concurrency}.")
        return shared["code_summaries"]
    
    async def exec_async(self, code_summary):
        await add_to_index(code_summary)
        return code_summary['file_path']

    async def post_async(self, shared, prep_res, exec_res_list):
        print(f"Knowledge Graph built successfully with {len(exec_res_list)} entries.")
        kg_data = get_knowledge_graph_data_for_saving()
        kg_data["project_analysis"] = shared.get("project_analysis", {})
        shared["knowledge_graph_data"] = kg_data