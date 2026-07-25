"""模型适配器占位与测试替身。"""

from asa_core.application.ports.model_port import ModelPort, ModelRequest, ModelResult


class ModelAdapterNotConfigured(ModelPort):
    """未配置供应商时显式失败，避免静默产出虚假分析结果。"""

    async def complete(self, request: ModelRequest) -> ModelResult:
        raise RuntimeError("未配置 ASA 模型适配器")

    def estimate_tokens(self, text: str) -> int:
        # 无 SDK 时使用保守字符估算，仅用于裁剪，不用于计费。
        return max(1, (len(text) + 2) // 3)

    async def health_check(self) -> bool:
        return False
