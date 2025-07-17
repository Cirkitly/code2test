from pocketflow import AsyncFlow
from nodes.analysis_nodes import DiscoverProjectNode, GenerateSummariesNode, BuildKnowledgeGraphNode

def create_offline_flow():
    """
    Creates the workflow for Phase 1: Indexing the codebase.
    This flow is run once to build the knowledge graph.
    """
    discover_node = DiscoverProjectNode()
    summarize_node = GenerateSummariesNode()
    build_kg_node = BuildKnowledgeGraphNode()

    # Define the flow sequence
    discover_node >> summarize_node >> build_kg_node
    
    offline_flow = AsyncFlow(start=discover_node)
    return offline_flow