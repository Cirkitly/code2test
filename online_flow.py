from pocketflow import AsyncFlow, Node
from nodes.generation_nodes import PlanTestsNode, GenerateSingleTestNode, HealNode, MultiToolRouterNode, LearningEngineNode
from nodes.verification_nodes import VerifySingleTestNode, QualityGateNode, HumanInTheLoopNode
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
    --- PHASE 5 LEARNING FLOW ---
    Creates the workflow for generating, validating, verifying, healing, escalating, and learning from a single test case.
    The flow is: Route -> Generate -> QualityGate -> Verify -> [Heal] -> Verify -> [Escalate] -> Learn
    """
    router_node = MultiToolRouterNode()
    generate_node = GenerateSingleTestNode()
    quality_gate_node = QualityGateNode()
    verify_node_initial = VerifySingleTestNode(name="verify_initial")
    heal_node = HealNode()
    verify_node_healed = VerifySingleTestNode(name="verify_healed")
    human_in_the_loop_node = HumanInTheLoopNode()
    learning_node = LearningEngineNode()

    # 1. Route, Generate, and Validate the test
    router_node >> generate_node >> quality_gate_node >> verify_node_initial

    # 2. If initial verification fails, go to heal
    verify_node_initial.on_failure >> heal_node

    # 3. If heal is successful, re-verify the test
    heal_node.on_success >> verify_node_healed

    # 4. All failure paths lead to escalation
    verify_node_healed.on_failure >> human_in_the_loop_node
    quality_gate_node.on_failure >> human_in_the_loop_node
    heal_node.on_failure >> human_in_the_loop_node

    # 5. All final nodes (success or escalation) lead to the learning engine
    verify_node_initial.on_success >> learning_node
    verify_node_healed.on_success >> learning_node
    human_in_the_loop_node.on_success >> learning_node

    execution_flow = AsyncFlow(start=router_node)
    return execution_flow