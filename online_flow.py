from pocketflow import AsyncFlow, Node
from nodes.generation_nodes import PlanTestsNode, GenerateUnitTestsNode, HealNode
from nodes.verification_nodes import VerifyTestsNode, FinalizeAndOrganizeNode
import json

class LoadContextNode(Node):
    """
    This node loads the necessary context (like project_analysis) from the
    persisted knowledge graph file before the online phase begins.
    """
    def prep(self, shared):
        # FIX: Get kg_path from params, which is set by main.py
        return self.params.get("knowledge_graph_path")

    def exec(self, prep_res):
        kg_path = prep_res
        if not kg_path:
            raise ValueError("knowledge_graph_path must be provided in flow params.")
            
        print(f"Loading context from {kg_path}...")
        with open(kg_path, 'r', encoding='utf-8') as f:
            kg_data = json.load(f)
        
        return kg_data.get("project_analysis", {})

    def post(self, shared, prep_res, exec_res):
        shared["project_analysis"] = exec_res
        print("Context loaded successfully.")

def create_online_flow():
    """
    Creates the workflow for Phase 2: Generating and healing tests.
    """
    load_context_node = LoadContextNode()
    plan_node = PlanTestsNode()
    generate_node = GenerateUnitTestsNode()
    verify_node = VerifyTestsNode()
    heal_node = HealNode()
    finalize_node = FinalizeAndOrganizeNode()

    load_context_node >> plan_node
    plan_node >> generate_node
    generate_node >> verify_node
    
    verify_node - "success" >> finalize_node
    verify_node - "failure" >> heal_node
    
    heal_node >> generate_node

    online_flow = AsyncFlow(start=load_context_node)
    return online_flow