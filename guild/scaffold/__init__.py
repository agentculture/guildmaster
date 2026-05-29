"""Scaffold helpers for ``guild create`` — template-instantiate approach.

This package provides the PURE transform layer (no network, no subprocess, no
filesystem side-effects beyond the destination tree) used by ``guild create`` to
customise a freshly-cloned copy of ``agentculture/culture-agent-template`` into a
new sibling agent.

Public surface
--------------
``instantiate`` — the transform module:
    transform_clone(dest, bare, desc, backend="claude", dist=None, command=None, pkg=None) -> None
    rename_map(bare, pkg=None) -> dict[str, str]
    transform_plan(bare, desc, dist=None, command=None, pkg=None) -> dict
"""
