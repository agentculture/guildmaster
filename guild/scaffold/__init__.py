"""Scaffold helpers for ``guild create`` — template-instantiate approach.

This package provides the PURE transform layer (no network, no subprocess, no
filesystem side-effects beyond the destination tree) used by ``guild create`` to
customise a freshly-cloned copy of ``agentculture/culture-agent-template`` into a
new sibling agent.

Public surface
--------------
``instantiate`` — the transform module:
    transform_clone(dest, pkg, repo_token, desc, backend) -> None
    rename_map(bare) -> dict[str, str]
    transform_plan(bare, desc) -> dict
"""
