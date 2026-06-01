"""
suggest_action.py — the signature differentiator: a concrete "what to do" per opportunity.

Two backends, auto-selected:
  * template  (default, free, offline) — rule-based draft keyed on opp_type/source
  * claude    (used iff ANTHROPIC_API_KEY is set) — calls claude-haiku for a sharper draft

Results are cached by opportunity id (in-memory + SQLite-free dict) so re-renders and
the brief export don't pay twice.
"""
from __future__ import annotations
import os, textwrap

_CACHE: dict[str, str] = {}

_TEMPLATES = {
    ("github", "issue"): (
        "Comment on this issue: confirm you can reproduce on {first_tag}, share your "
        "environment, and offer to open a PR. Starter line: \"I hit this too on "
        "{first_tag}; happy to take a crack at a fix — is the approach in the thread the "
        "preferred one?\""
    ),
    ("github", "pr"): (
        "Review this PR: pull the branch, run the test suite, and leave one concrete "
        "improvement on the {first_tag} path. A thoughtful review on an active PR is high "
        "visibility with maintainers."
    ),
    ("github", "discussion"): (
        "Add a substantive reply sharing how you solved {first_tag} in production, with a "
        "short code snippet. Discussions reward depth over speed."
    ),
    ("reddit", "post"): (
        "Write a top-level comment with a contrarian-but-supported take on {first_tag}. "
        "Hook: \"Most {domain} threads miss that ...\" then back it with one specific example."
    ),
    ("reddit", "discussion"): (
        "Share a 3-bullet teardown of your {first_tag} setup. Reddit upvotes concrete, "
        "reproducible detail."
    ),
    ("hackernews", "post"): (
        "Post a comment that adds a data point the article lacks about {first_tag}. HN "
        "rewards first-hand numbers — lead with yours."
    ),
    ("hackernews", "show"): (
        "Try the project, then comment with specific, kind feedback plus one feature idea "
        "for {first_tag}. Makers remember useful Show HN feedback."
    ),
}

_DEFAULT = ("Engage authentically: add one concrete, first-hand insight about "
            "{first_tag} that the thread is missing.")


def _template_action(opp: dict) -> str:
    tags = opp.get("tags") or []
    first_tag = tags[0] if tags else opp.get("domain", "this topic")
    key = (opp.get("source"), opp.get("opp_type"))
    tmpl = _TEMPLATES.get(key, _DEFAULT)
    return tmpl.format(first_tag=first_tag, domain=opp.get("domain", ""))


def _claude_action(opp: dict) -> str:
    """Optional: sharper draft via the Anthropic API. Requires ANTHROPIC_API_KEY."""
    from anthropic import Anthropic
    client = Anthropic()
    prompt = textwrap.dedent(f"""
        You are an expert dev-community strategist. In <=3 sentences, give a concrete
        action a professional should take on this online opportunity to build career
        capital. Be specific; include a one-line draft they could paste.

        SOURCE: {opp.get('source')}  TYPE: {opp.get('opp_type')}  DOMAIN: {opp.get('domain')}
        TITLE: {opp.get('title')}
        SNIPPET: {(opp.get('body') or '')[:300]}
    """).strip()
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def suggest_action(opp: dict, prefer_claude: bool | None = None) -> str:
    oid = opp.get("id", "")
    if oid in _CACHE:
        return _CACHE[oid]
    use_claude = (os.getenv("ANTHROPIC_API_KEY") is not None) if prefer_claude is None else prefer_claude
    text = None
    if use_claude:
        try:
            text = _claude_action(opp)
        except Exception:
            text = None  # fall back silently to template
    if not text:
        text = _template_action(opp)
    _CACHE[oid] = text
    return text


def backend_name() -> str:
    return "claude-haiku-4-5" if os.getenv("ANTHROPIC_API_KEY") else "template (free)"
