#!/usr/bin/env bash
set -euo pipefail
# configure-repo — apply guildmaster's standard GitHub repo config to a sibling.
#
# GitHub template instantiation copies files + branches but NOT repo settings,
# so `guild create` must apply these itself after the repo exists. This is the
# deterministic config layer, mirroring guildmaster's own setup:
#
#   1. delete_branch_on_merge = true   (auto-delete head branches on merge)
#   2. environments: pypi, testpypi    (Trusted Publishing targets for publish.yml)
#   3. ruleset "Protect main"          (block deletion + non-fast-forward; require a PR)
#   4. secret SONAR_TOKEN              (created EMPTY if absent; never clobbers an
#                                       existing value — override it in the GitHub UI)
#
# Idempotent: the ruleset is created only if no ruleset of that name exists, and
# the secret is set only if it is not already present. Dry-run by default.
#
# Usage:
#   configure-repo.sh <owner/repo>            # dry-run: print what it WOULD do
#   configure-repo.sh <owner/repo> --apply    # apply via gh
#
# Exit codes: 0 success · 1 usage / environment error.

RULESET_NAME="Protect main"
SONAR_SECRET="SONAR_TOKEN"
ENVIRONMENTS=(pypi testpypi)

repo=""
apply=false
for arg in "$@"; do
    case "$arg" in
        --apply) apply=true ;;
        -*) echo "configure-repo: unknown flag: $arg" >&2; exit 1 ;;
        *) repo="$arg" ;;
    esac
done

if [ -z "$repo" ]; then
    echo "usage: configure-repo.sh <owner/repo> [--apply]" >&2
    exit 1
fi
command -v gh >/dev/null 2>&1 || { echo "configure-repo: 'gh' not on PATH" >&2; exit 1; }

say() { if $apply; then echo "  ✓ $1"; else echo "  would: $1"; fi; }

echo "── configure-repo: $repo $([ "$apply" = true ] && echo '(--apply)' || echo '(dry-run)') ──"

# 1. auto-delete-on-merge ---------------------------------------------------
say "set delete_branch_on_merge = true"
if $apply; then
    gh api -X PATCH "repos/$repo" -F delete_branch_on_merge=true >/dev/null
fi

# 2. environments -----------------------------------------------------------
for env in "${ENVIRONMENTS[@]}"; do
    say "ensure environment '$env'"
    if $apply; then
        gh api -X PUT "repos/$repo/environments/$env" >/dev/null
    fi
done

# 3. ruleset "Protect main" (idempotent by name) ----------------------------
existing="$(gh api "repos/$repo/rulesets" --jq '.[].name' 2>/dev/null || true)"
if printf '%s\n' "$existing" | grep -Fxq "$RULESET_NAME"; then
    echo "  • ruleset '$RULESET_NAME' already present — skipping"
else
    say "create ruleset '$RULESET_NAME' (deletion + non_fast_forward + pull_request)"
    if $apply; then
        gh api -X POST "repos/$repo/rulesets" --input - >/dev/null <<JSON
{
  "name": "$RULESET_NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    }
  ]
}
JSON
    fi
fi

# 4. SONAR_TOKEN secret (empty placeholder; never clobber an override) -------
if gh secret list --repo "$repo" 2>/dev/null | grep -q "^${SONAR_SECRET}\b"; then
    echo "  • secret '$SONAR_SECRET' already set — leaving it (override lives in GitHub)"
else
    say "create empty secret '$SONAR_SECRET' (override it in the GitHub UI)"
    if $apply; then
        printf '' | gh secret set "$SONAR_SECRET" --repo "$repo" >/dev/null
    fi
fi

echo "── done ──"
