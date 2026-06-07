from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from tracker.events import ActivityChunk, ChunkSummary, FinalPseudocode


class LLMClient(ABC):
    @abstractmethod
    def summarize_chunk(self, chunk: ActivityChunk) -> ChunkSummary:
        raise NotImplementedError

    @abstractmethod
    def generate_final_pseudocode(self, summaries: list[ChunkSummary]) -> FinalPseudocode:
        raise NotImplementedError

    def generate_final_pseudocode_with_audio(
        self,
        summaries: list[ChunkSummary],
        audio_path: Path | None,
    ) -> FinalPseudocode:
        return self.generate_final_pseudocode(summaries)
