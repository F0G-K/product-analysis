from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from backend.core.enums import ConfidenceLevel, EvidenceType


class EvidenceLinker:
    """校验证据引用，禁止把无法定位的内容标成事实。"""

    def link(
        self,
        llm_result: Mapping[str, Any],
        retrieved_docs: Sequence[Mapping[str, Any]],
    ) -> tuple[Mapping[str, Any], ...]:
        valid_citations = self._citation_index(retrieved_docs)
        linked: list[Mapping[str, Any]] = []

        raw_evidence = llm_result.get("evidence", [])
        if not isinstance(raw_evidence, Sequence) or isinstance(raw_evidence, str):
            raw_evidence = []

        for item in raw_evidence:
            if not isinstance(item, Mapping):
                continue
            evidence_type = self._normalize_type(item.get("evidence_type"))
            citation = self._normalize_optional_text(item.get("citation_location"))
            if evidence_type == EvidenceType.FACT and citation not in valid_citations:
                # 引用无法回查时只能作为模型推断，不能伪装成输入事实。
                evidence_type = EvidenceType.INFERENCE
                citation = None

            linked.append(
                {
                    "evidence_type": evidence_type.value,
                    "citation_location": citation,
                    "content_summary": self._normalize_optional_text(
                        item.get("content_summary")
                    ),
                    "excerpt_text": self._normalize_optional_text(item.get("excerpt_text")),
                    "related_conclusion_id": self._normalize_optional_text(
                        item.get("related_conclusion_id")
                    ),
                }
            )

        if not linked:
            linked.append(
                {
                    "evidence_type": EvidenceType.MISSING.value,
                    "citation_location": None,
                    "content_summary": "当前材料不足，无法形成可回查证据",
                    "excerpt_text": None,
                    "related_conclusion_id": None,
                }
            )
        return tuple(linked)

    @staticmethod
    def _citation_index(
        documents: Sequence[Mapping[str, Any]],
    ) -> frozenset[str]:
        citations: set[str] = set()
        for document in documents:
            citation = document.get("citation")
            if isinstance(citation, str) and citation.strip():
                citations.add(citation.strip())
        return frozenset(citations)

    @staticmethod
    def _normalize_type(value: Any) -> EvidenceType:
        try:
            return EvidenceType(str(value))
        except ValueError:
            return EvidenceType.INFERENCE

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None


class ConfidenceAssessor:
    def assess(self, evidence: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        fact_count = sum(item.get("evidence_type") == EvidenceType.FACT for item in evidence)
        inference_count = sum(
            item.get("evidence_type") == EvidenceType.INFERENCE for item in evidence
        )
        missing_count = sum(
            item.get("evidence_type") == EvidenceType.MISSING for item in evidence
        )

        if fact_count >= 2 and inference_count == 0 and missing_count == 0:
            level = ConfidenceLevel.HIGH
        elif fact_count >= 1 and missing_count == 0:
            level = ConfidenceLevel.MEDIUM
        else:
            level = ConfidenceLevel.LOW

        return {
            "level": level.value,
            "fact_count": fact_count,
            "inference_count": inference_count,
            "missing_count": missing_count,
        }

