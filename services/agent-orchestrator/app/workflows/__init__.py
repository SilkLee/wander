"""Workflows package."""

from app.workflows.langgraph_flow import build_langgraph_flow, build_triage_graph, run_langgraph

try:
    from app.workflows.processor import WorkflowProcessor
except ImportError:  # langchain deps may not be installed
    WorkflowProcessor = None  # type: ignore[assignment,misc]

__all__ = ["WorkflowProcessor", "build_langgraph_flow", "build_triage_graph", "run_langgraph"]
