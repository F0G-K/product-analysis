"""LangGraph 单角色执行图适配器。"""

from typing import Any, TypedDict

from asa_core.application.ports.model_port import ModelPort, ModelRequest, ModelResult
from langgraph.graph import END, START, StateGraph


class _RoleGraphState(TypedDict):
    request: ModelRequest
    result: ModelResult | None


class LangGraphModelAdapter(ModelPort):
    """只编排一次角色调用，不接触项目、阶段或任务持久化状态。"""

    def __init__(self, delegate: ModelPort) -> None:
        self._delegate = delegate
        graph: StateGraph[Any] = StateGraph(_RoleGraphState)
        graph.add_node("model_call", self._call_model)
        graph.add_edge(START, "model_call")
        graph.add_edge("model_call", END)
        self._graph = graph.compile()

    async def _call_model(self, state: _RoleGraphState) -> dict[str, ModelResult]:
        return {"result": await self._delegate.complete(state["request"])}

    async def complete(self, request: ModelRequest) -> ModelResult:
        state = await self._graph.ainvoke({"request": request, "result": None})
        result = state.get("result")
        if not isinstance(result, ModelResult):
            raise RuntimeError("LangGraph 未返回模型结果")
        return result

    def estimate_tokens(self, text: str) -> int:
        return self._delegate.estimate_tokens(text)

    async def health_check(self) -> bool:
        return await self._delegate.health_check()

    async def close(self) -> None:
        close = getattr(self._delegate, "close", None)
        if close is not None:
            await close()
