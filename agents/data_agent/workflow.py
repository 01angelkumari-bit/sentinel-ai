from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from .agent import DataAgent
from .config import DataAgentSettings
from .models import DataAgentState


def make_data_agent_node(settings: DataAgentSettings):
    agent = DataAgent(settings)

    def data_agent_node(state: DataAgentState) -> dict[str, Any]:
        organization_id = state.get("organization_id")
        if not organization_id:
            raise ValueError("organization_id is required in LangGraph state")
        output = agent.run(organization_id=organization_id, request_id=state.get("request_id"), query_parameters=state.get("query_parameters"))
        serialized = output.model_dump(mode="json")
        return {
            "request_id": output.metadata.request_id,
            "organization_id": organization_id,
            "data_agent_output": serialized,
            "cleaned_data": serialized["cleaned_data"],
            "quality_report": serialized["quality_report"],
            "validation_summary": serialized["validation_summary"],
            "next_agents": output.metadata.downstream_agents if output.success else [],
            "warnings": output.warnings,
            "errors": output.errors,
        }

    return data_agent_node


def distribute_node(state: DataAgentState) -> dict[str, Any]:
    """Create immutable consumer envelopes; downstream nodes read the same trusted dataset."""
    envelope = {
        "request_id": state.get("request_id"),
        "organization_id": state.get("organization_id"),
        "cleaned_data": state.get("cleaned_data", []),
        "quality_report": state.get("quality_report", {}),
        "validation_summary": state.get("validation_summary", {}),
    }
    return {"distribution": {agent_name: envelope.copy() for agent_name in state.get("next_agents", [])}}


def build_data_workflow(settings: DataAgentSettings):
    builder = StateGraph(DataAgentState)
    builder.add_node("data_agent", make_data_agent_node(settings))
    builder.add_node("distribute", distribute_node)
    builder.add_edge(START, "data_agent")
    builder.add_edge("data_agent", "distribute")
    builder.add_edge("distribute", END)
    return builder.compile(name="sentinel_data_agent_workflow")


@lru_cache(maxsize=8)
def workflow_from_yaml(config_path: str):
    return build_data_workflow(DataAgentSettings.from_yaml(config_path))
