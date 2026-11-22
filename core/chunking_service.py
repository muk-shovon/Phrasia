"""Provider-aware document chunking with protected spans."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from phrasia_domain import ChunkPlan, ProtectedSpan


CHARACTERS_PER_TOKEN_ESTIMATE = 3.5
DEFAULT_OUTPUT_RESERVE_TOKENS = 200
DEFAULT_SAFETY_MARGIN_PCT = 0.15
DEFAULT_MAX_INPUT_TOKENS = 4000


@dataclass
class _Seg:
    s_start: int
    s_end: int
    is_placeholder: bool
    placeholder_idx: Optional[int]
    masked_len: int


class Chunker:
    """Splits document text into provider-compatible chunks respecting boundaries and protected spans."""

    def __init__(
        self,
        max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS,
        output_reserve_tokens: int = DEFAULT_OUTPUT_RESERVE_TOKENS,
        safety_margin_pct: float = DEFAULT_SAFETY_MARGIN_PCT,
    ):
        self.max_input_tokens = max_input_tokens
        self.output_reserve_tokens = output_reserve_tokens
        self.safety_margin_pct = safety_margin_pct

    # ── public API ──────────────────────────────────────────────────────────────

    def chunk(self, text: str) -> list[ChunkPlan]:
        if not text.strip():
            return []
        protected = self._extract_protected_spans(text)
        segments = self._build_segments(text, protected)
        boundaries = [i for i in range(len(text) - 1) if text[i:i+2] == "\n\n"]
        para_groups = self._split_at_boundaries(segments, boundaries)
        budget_chunks = self._budget_split(para_groups)
        return [self._make_plan(i, run, text, protected) for i, run in enumerate(budget_chunks)]

    @staticmethod
    def safe_chunk_size_chars(
        max_in: int = DEFAULT_MAX_INPUT_TOKENS,
        out_res: int = DEFAULT_OUTPUT_RESERVE_TOKENS,
        margin: float = DEFAULT_SAFETY_MARGIN_PCT,
    ) -> int:
        return int((max_in - out_res) * CHARACTERS_PER_TOKEN_ESTIMATE * (1 - margin))

    # ── internals ───────────────────────────────────────────────────────────────

    @classmethod
    def _extract_protected_spans(cls, text: str) -> list[ProtectedSpan]:
        spans: list[ProtectedSpan] = []
        seen: set[tuple[int, int]] = set()
        patterns = [
            (r"https?://[^\s\x00<>\"')\]}>,;]+", "url"),
            (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email"),
            (r"`[^`\n]+`", "code_inline"),
            (r">>[^\n]*", "quote"),
            (r"\[[\d,]+\]", "ref_marker"),
        ]
        for pat, ptype in patterns:
            for m in re.finditer(pat, text, re.MULTILINE):
                s, e = m.start(), m.end()
                if (s, e) in seen:
                    continue
                seen.add((s, e))
                placeholder = f"\x00_P_{len(spans)}_\x00"
                spans.append(ProtectedSpan(
                    span_id=f"{ptype}_{len(spans)}",
                    start_offset=s, end_offset=e,
                    span_type=ptype,
                    original_text=m.group(),
                    placeholder=placeholder,
                ))
        spans.sort(key=lambda s: s.start_offset)
        return spans

    @classmethod
    def _build_segments(cls, text: str, spans: list[ProtectedSpan]) -> list[_Seg]:
        segs: list[_Seg] = []
        pos = 0
        for i, sp in enumerate(spans):
            if sp.start_offset > pos:
                segs.append(_Seg(pos, sp.start_offset, False, None, sp.start_offset - pos))
            segs.append(_Seg(sp.start_offset, sp.end_offset, True, i, len(sp.placeholder)))
            pos = sp.end_offset
        if pos < len(text):
            segs.append(_Seg(pos, len(text), False, None, len(text) - pos))
        return segs

    @classmethod
    def _split_at_boundaries(cls, segments: list[_Seg], boundaries: list[int]) -> list[list[_Seg]]:
        if not segments:
            return []
        # A new paragraph begins at b+2 for every "\n\n" at index b.
        # Protected spans never contain "\n\n", so every boundary is fully
        # inside one non-placeholder segment. Split those segments at the
        # paragraph-start positions; placeholders stay atomic.
        cuts = sorted({b + 2 for b in boundaries})
        result: list[list[_Seg]] = []
        current: list[_Seg] = []
        for seg in segments:
            if seg.is_placeholder:
                current.append(seg)
                if seg.s_end in cuts:
                    result.append(current)
                    current = []
                continue
            prev = seg.s_start
            for c in cuts:
                if not (seg.s_start < c < seg.s_end):
                    continue
                current.append(_Seg(prev, c, False, None, c - prev))
                result.append(current)
                current = []
                prev = c
            if prev < seg.s_end:
                current.append(_Seg(prev, seg.s_end, False, None, seg.s_end - prev))
            if seg.s_end in cuts:
                result.append(current)
                current = []
        if current:
            result.append(current)
        return result

    def _budget_split(self, groups: list[list[_Seg]]) -> list[list[_Seg]]:
        budget = self.safe_chunk_size_chars(self.max_input_tokens,
                                            self.output_reserve_tokens,
                                            self.safety_margin_pct)
        if budget <= 0:
            budget = 1500
        result: list[list[_Seg]] = []
        cur: list[_Seg] = []
        cur_len = 0
        for grp in groups:
            grp_len = sum(s.masked_len for s in grp)
            if cur and cur_len + grp_len + 2 > budget:
                result.append(cur)
                cur = []
                cur_len = 0
            cur.extend(grp)
            cur_len += grp_len + 2
        if cur:
            result.append(cur)
        return result if result else ([groups[0]] if groups else [])

    def _make_plan(self, idx: int, run: list[_Seg],
                   text: str, protected: list[ProtectedSpan]) -> ChunkPlan:
        source_text = ""
        for seg in run:
            if seg.is_placeholder:
                source_text += protected[seg.placeholder_idx].original_text
            else:
                source_text += text[seg.s_start:seg.s_end]
        start_off = run[0].s_start if run else 0
        end_off = run[-1].s_end if run else 0
        return ChunkPlan(
            chunk_id=f"chunk-{idx:04d}",
            sequence_index=idx,
            source_start_offset=start_off,
            source_end_offset=end_off,
            source_text=source_text,
            source_hash=hashlib.sha256(source_text.encode()).hexdigest()[:12],
            protected_spans=[ps for ps in protected
                             if ps.start_offset >= start_off and ps.end_offset <= end_off],
        )