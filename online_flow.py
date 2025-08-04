from pocketflow import AsyncFlow, Node
from nodes.generation_nodes import PlanTestsNode, GenerateSingleTestNode
from nodes.verification_nodes import VerifySingleTestNode
import json

class LoadContextNode(Node):
    """
    This node loads the necessary context (like project_analysis) from the
    persisted knowledge graph file before the online phase begins.
    """
    def prep(self, shared):
        return self.params.get("knowledge_graph_path")

    def exec(self, kg_path):
        if not kg_path:
            raise ValueError("knowledge_graph_path must be provided in flow params.")

        print(f"Loading context from {kg_path}...")
        try:
            with open(kg_path, 'r', encoding='utf-8') as f:
                kg_data = json.load(f)
            return kg_data.get("project_analysis", {})
        except FileNotFoundError:
            print(f"Error: Knowledge graph file not found at {kg_path}")
            raise
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {kg_path}")
            raise

    def post(self, shared, prep_res, exec_res):
        shared["project_analysis"] = exec_res
        print("Context loaded successfully.")


def create_planning_flow():
    """
    --- PHASE 1 NEW FLOW ---
    Creates the workflow for the initial planning phase.
    """
    load_context_node = LoadContextNode()
    plan_node = PlanTestsNode()

    load_context_node >> plan_node

    planning_flow = AsyncFlow(start=load_context_node)
    return planning_flow


def create_single_test_execution_flow():
    """
    --- PHASE 1 NEW FLOW ---
    Creates the workflow for generating and verifying a single test case.
    In Phase 2, this flow will be expanded to include the healing loop.
    """
    generate_node = GenerateSingleTestNode()
    verify_node = VerifySingleTestNode()

    generate_node >> verify_node

    # In Phase 2, the 'failure' branch from verify_node will go to a HealNode.
    # For now, failures are handled by the main.py orchestration loop.

    execution_flow = AsyncFlow(start=generate_node)
    return execution_flow