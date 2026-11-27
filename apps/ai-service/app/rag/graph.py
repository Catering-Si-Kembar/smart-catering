from __future__ import annotations

import importlib
from typing import Any, TypedDict

from app.contracts import RagChatData, RagSourceItem
from app.rag.guardrails import detect_input_guardrail, log_security_event
from app.rag.ports import (
    LLMClientPort,
    RagConfigurationError,
    RagRateLimitError,
    RagTimeoutError,
    RagUpstreamError,
    RelevanceClassifierPort,
)
from app.rag.prompts import (
    FALLBACK_RATE_LIMIT_REPLY,
    FALLBACK_UNAVAILABLE_REPLY,
    FORBIDDEN_DATA_REPLY,
    NOT_FOUND_REPLY,
    OUT_OF_DOMAIN_REPLY,
    SECURITY_REJECTION_REPLY,
    build_agent_messages,
)
from app.rag.schemas import AgentContext, ToolCallRequest
from app.rag.tools import ToolRegistry


class AgentGraphState(TypedDict, total=False):
    """Typed state flowing through the LangGraph Agentic RAG StateGraph."""

    message: str
    context: AgentContext
    messages: list[dict[str, Any]]
    pending_tool_calls: list[ToolCallRequest]
    tools_called: list[str]
    sources: list[RagSourceItem]
    tokens_used: int
    iterations: int
    is_relevant: bool
    is_fallback: bool
    any_forbidden: bool
    any_found: bool
    any_not_found: bool
    final_reply: str | None


def uses_langgraph_runtime() -> bool:
    """Return True when optional extra `rag` (langgraph) is installed in the environment."""
    try:
        importlib.import_module("langgraph.graph")
    except ImportError:
        return False
    return True


class AgenticRagGraph:
    """Dual-source Agentic RAG orchestrator backed by LangGraph StateGraph when available."""

    def __init__(
        self,
        *,
        relevance_classifier: RelevanceClassifierPort,
        tool_registry: ToolRegistry,
        llm_client: LLMClientPort,
        timeout_seconds: float = 15.0,
        max_tool_iterations: int = 3,
    ) -> None:
        self._relevance_classifier = relevance_classifier
        self._tool_registry = tool_registry
        self._llm_client = llm_client
        self._timeout_seconds = timeout_seconds
        self._max_tool_iterations = max_tool_iterations
        self._compiled_graph: Any = self._build_langgraph()

    def _build_langgraph(self) -> Any:
        try:
            lg_graph = importlib.import_module("langgraph.graph")
        except ImportError:
            return None

        state_graph = lg_graph.StateGraph(AgentGraphState)
        state_graph.add_node("guardrail_check", self._node_guardrail_check)
        state_graph.add_node("relevance_gate", self._node_relevance_gate)
        state_graph.add_node("agent_reason", self._node_agent_reason)
        state_graph.add_node("execute_tools", self._node_execute_tools)
        state_graph.add_node("finalize", self._node_finalize)

        state_graph.add_edge(lg_graph.START, "guardrail_check")
        state_graph.add_conditional_edges(
            "guardrail_check",
            self._route_after_guardrail,
            {"blocked": "finalize", "continue": "relevance_gate"},
        )
        state_graph.add_conditional_edges(
            "relevance_gate",
            self._route_after_relevance,
            {"out_of_domain": "finalize", "continue": "agent_reason"},
        )
        state_graph.add_conditional_edges(
            "agent_reason",
            self._route_after_reason,
            {"call_tools": "execute_tools", "done": "finalize"},
        )
        state_graph.add_conditional_edges(
            "execute_tools",
            self._route_after_tools,
            {"done": "finalize", "continue": "agent_reason"},
        )
        state_graph.add_edge("finalize", lg_graph.END)
        return state_graph.compile()

    async def run(self, *, message: str, context: AgentContext) -> RagChatData:
        """Execute the Agentic RAG pipeline end-to-end and return a typed RagChatData contract."""
        initial_state: AgentGraphState = {
            "message": message,
            "context": context,
            "messages": [],
            "pending_tool_calls": [],
            "tools_called": [],
            "sources": [],
            "tokens_used": 0,
            "iterations": 0,
            "is_relevant": True,
            "is_fallback": False,
            "any_forbidden": False,
            "any_found": False,
            "any_not_found": False,
            "final_reply": None,
        }

        if self._compiled_graph is not None:
            final_state: AgentGraphState = await self._compiled_graph.ainvoke(initial_state)
        else:
            final_state = await self._run_fallback_state_machine(initial_state)

        deduped_tools = list(dict.fromkeys(final_state.get("tools_called", [])))
        deduped_sources = self._dedupe_sources(final_state.get("sources", []))
        tokens_total = final_state.get("tokens_used", 0)

        return RagChatData(
            reply=final_state.get("final_reply") or NOT_FOUND_REPLY,
            is_relevant=bool(final_state.get("is_relevant", False)),
            tools_called=deduped_tools,
            sources=deduped_sources,
            tokens_used=tokens_total if tokens_total > 0 else None,
            is_fallback=bool(final_state.get("is_fallback", False)),
        )

    async def _run_fallback_state_machine(self, state: AgentGraphState) -> AgentGraphState:
        """Deterministic state machine mirroring the exact LangGraph topology."""
        current: AgentGraphState = {**state, **(await self._node_guardrail_check(state))}
        if self._route_after_guardrail(current) == "blocked":
            return {**current, **(await self._node_finalize(current))}

        current = {**current, **(await self._node_relevance_gate(current))}
        if self._route_after_relevance(current) == "out_of_domain":
            return {**current, **(await self._node_finalize(current))}

        while True:
            current = {**current, **(await self._node_agent_reason(current))}
            if self._route_after_reason(current) == "done":
                break
            current = {**current, **(await self._node_execute_tools(current))}
            if self._route_after_tools(current) == "done":
                break

        return {**current, **(await self._node_finalize(current))}

    async def _node_guardrail_check(self, state: AgentGraphState) -> AgentGraphState:
        verdict = detect_input_guardrail(state["message"])
        if verdict.blocked:
            ctx = state["context"]
            log_security_event(
                category=verdict.category,
                user_role=ctx.user_role,
                conversation_id=ctx.conversation_id,
                request_id=ctx.request_id,
                detail=verdict.reason or "Blocked by input security guardrail.",
            )
            return {
                "is_relevant": False,
                "is_fallback": False,
                "final_reply": SECURITY_REJECTION_REPLY,
            }
        return {}

    def _route_after_guardrail(self, state: AgentGraphState) -> str:
        return "blocked" if state.get("final_reply") is not None else "continue"

    async def _node_relevance_gate(self, state: AgentGraphState) -> AgentGraphState:
        decision = await self._relevance_classifier.classify(state["message"])
        if not decision.is_relevant:
            return {
                "is_relevant": False,
                "is_fallback": False,
                "final_reply": OUT_OF_DOMAIN_REPLY,
            }

        ctx = state["context"]
        messages = build_agent_messages(
            user_role=ctx.user_role,
            message=state["message"],
            history=ctx.history,
        )
        return {
            "is_relevant": True,
            "messages": messages,
        }

    def _route_after_relevance(self, state: AgentGraphState) -> str:
        return "out_of_domain" if not state.get("is_relevant", False) else "continue"

    async def _node_agent_reason(self, state: AgentGraphState) -> AgentGraphState:
        iterations = state.get("iterations", 0)
        tool_schemas = (
            self._tool_registry.openai_tool_schemas()
            if iterations < self._max_tool_iterations
            else []
        )

        try:
            llm_response = await self._llm_client.generate_with_tools(
                messages=state["messages"],
                tools=tool_schemas,
                timeout_seconds=self._timeout_seconds,
            )
        except RagRateLimitError:
            return {
                "pending_tool_calls": [],
                "is_fallback": True,
                "final_reply": FALLBACK_RATE_LIMIT_REPLY,
            }
        except (RagTimeoutError, RagConfigurationError, RagUpstreamError):
            return {
                "pending_tool_calls": [],
                "is_fallback": True,
                "final_reply": FALLBACK_UNAVAILABLE_REPLY,
            }

        tokens = state.get("tokens_used", 0) + (llm_response.tokens_used or 0)

        if llm_response.tool_calls and iterations < self._max_tool_iterations:
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": llm_response.content,
                "tool_calls": [
                    {
                        "id": call.call_id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": call.arguments,
                        },
                    }
                    for call in llm_response.tool_calls
                ],
            }
            return {
                "messages": [*state["messages"], assistant_msg],
                "pending_tool_calls": llm_response.tool_calls,
                "tokens_used": tokens,
                "iterations": iterations + 1,
            }

        return {
            "pending_tool_calls": [],
            "tokens_used": tokens,
            "final_reply": llm_response.content or None,
        }

    def _route_after_reason(self, state: AgentGraphState) -> str:
        if state.get("pending_tool_calls"):
            return "call_tools"
        return "done"

    def _route_after_tools(self, state: AgentGraphState) -> str:
        return "done" if state.get("is_fallback") else "continue"

    async def _node_execute_tools(self, state: AgentGraphState) -> AgentGraphState:
        ctx = state["context"]
        next_messages = list(state["messages"])
        tools_called = list(state.get("tools_called", []))
        sources = list(state.get("sources", []))
        any_forbidden = bool(state.get("any_forbidden", False))
        any_found = bool(state.get("any_found", False))
        any_not_found = bool(state.get("any_not_found", False))

        for call in state.get("pending_tool_calls", []):
            try:
                outcome = await self._tool_registry.execute(call.name, call.arguments, ctx)
            except (RagTimeoutError, RagUpstreamError):
                return {
                    "pending_tool_calls": [],
                    "tools_called": [*tools_called, call.name],
                    "sources": sources,
                    "is_fallback": True,
                    "final_reply": FALLBACK_UNAVAILABLE_REPLY,
                }

            if outcome.status != "forbidden" or call.name in {
                "search_catering_knowledge",
                "get_order_details",
                "get_production_schedule",
                "get_invoice_and_payment_status",
            }:
                tools_called.append(call.name)

            sources.extend(outcome.sources)
            if outcome.forbidden:
                any_forbidden = True
            if outcome.status == "ok":
                any_found = True
            if outcome.not_found:
                any_not_found = True

            next_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.call_id,
                    "name": call.name,
                    "content": outcome.content_for_llm,
                }
            )

        return {
            "messages": next_messages,
            "pending_tool_calls": [],
            "tools_called": tools_called,
            "sources": sources,
            "any_forbidden": any_forbidden,
            "any_found": any_found,
            "any_not_found": any_not_found,
        }

    async def _node_finalize(self, state: AgentGraphState) -> AgentGraphState:
        if state.get("is_fallback") or not state.get("is_relevant", False):
            return {}

        if state.get("any_forbidden") and not state.get("any_found"):
            return {"final_reply": FORBIDDEN_DATA_REPLY}

        if state.get("any_not_found") and not state.get("any_found"):
            return {"final_reply": NOT_FOUND_REPLY}

        reply = (state.get("final_reply") or "").strip()
        if not reply:
            return {"final_reply": NOT_FOUND_REPLY}
        return {"final_reply": reply}

    def _dedupe_sources(self, items: list[RagSourceItem]) -> list[RagSourceItem]:
        seen: set[tuple[str, str, str | None, str | None]] = set()
        unique: list[RagSourceItem] = []
        for item in items:
            key = (item.source, item.category, item.chunk_id, item.reference_id)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique
