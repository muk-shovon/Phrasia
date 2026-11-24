"""Compatibility shim - see rewrite_diff.py for implementation."""
from backend.core.rewrite_diff import *  # noqa: F401,F403
from backend.core.rewrite_diff import diff_segments, diff_from_alignment, style_report, _risk, _punct_only_change, _norm_ws  # noqa: F401
