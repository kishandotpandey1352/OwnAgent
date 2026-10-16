from langgraph.graph import END, START, StateGraph

from app.graphs.state import FinanceAgentState
from app.nodes.audit_agent_run import audit_agent_run_node
from app.nodes.generate_answer import generate_answer_node
from app.nodes.load_memory import load_memory_node
from app.nodes.plan_tools import plan_tools_node
from app.nodes.run_tools import run_tools_node
from app.nodes.validate_grounding import validate_grounding_node


def build_finance_memory_graph():
    graph = StateGraph(FinanceAgentState)

    graph.add_node("load_memory", load_memory_node)
    graph.add_node("plan_tools", plan_tools_node)
    graph.add_node("run_tools", run_tools_node)
    graph.add_node("generate_answer", generate_answer_node)
    graph.add_node("audit_agent_run", audit_agent_run_node)
    graph.add_node("validate_grounding", validate_grounding_node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "plan_tools")
    graph.add_edge("plan_tools", "run_tools")
    graph.add_edge("run_tools", "generate_answer")
    graph.add_edge("generate_answer", "validate_grounding")
    graph.add_edge("validate_grounding", "audit_agent_run")
    graph.add_edge("audit_agent_run", END)

    return graph.compile()