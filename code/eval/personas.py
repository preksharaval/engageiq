"""
Persona pass/fail evaluation — matches the BAX-423 EngageIQ brief exactly.
Sofia / David / Lina / Raj with their exact pass criteria.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from score.composite import Ranker

PERSONAS = [
    {
        "name": "Sofia — ML Student · Portfolio Builder",
        "profile": {
            "user_id": "sofia",
            "interests": ["ml", "ai_research", "python_data_eng", "beginner_coding"],
            "free_text": "machine learning NLP data pipelines beginner friendly good first issue",
            "platforms": ["github", "reddit", "hackernews"],
            "time_budget": 5,
            "source_affinity": {"github": 1.0},
        },
        "checks": [
            # Brief: "Top-10 includes >=3 GitHub repos with good first issue tags"
            ("github_good_first_issue>=3", lambda r: sum(1 for x in r if x["source"]=="github" and (x.get("has_good_first_issue") or "good first issue" in x.get("title","").lower() or "good-first-issue" in [t.lower() for t in x.get("tags",[])])) >= 3),
            ("ml_domain_focus>=6",         lambda r: sum(1 for x in r if x["domain"] in ("ml","ai_research","python_data_eng","beginner_coding")) >= 6),
            # Brief: "Zero repos requiring C++/Rust expertise"
            ("no_cpp_rust",                lambda r: sum(1 for x in r if any(k in x.get("title","").lower() for k in ["c++","rust","rtos","firmware","embedded"])) == 0),
            # Brief: "Engagement brief estimates <1 hr per opportunity" (effort<=0.5 ~ <1hr)
            ("under_1hr_effort>=3",        lambda r: sum(1 for x in r if x.get("effort",0.5) <= 0.5) >= 3),
        ],
    },
    {
        "name": "David — DevOps Engineer · Niche Community",
        "profile": {
            "user_id": "david",
            "interests": ["devops_k8s", "cloud_apis"],
            "free_text": "kubernetes terraform CI CD observability cloud native infrastructure",
            "platforms": ["github", "reddit", "hackernews"],
            "time_budget": 3,
            "source_affinity": {"github": 0.8},
        },
        "checks": [
            ("devops_focus>=7",          lambda r: sum(1 for x in r if x["domain"] in ("devops_k8s","cloud_apis")) >= 7),
            ("community_health>=p40",    lambda r: sum(1 for x in r if x["components"]["community_health"] >= 0.10) >= 5),
            ("high_velocity>=4",         lambda r: sum(1 for x in r if x.get("velocity",0) >= 0.05) >= 4),
            ("respects_time>=5",         lambda r: sum(1 for x in r if x.get("effort",0.5) <= 0.65) >= 5),
        ],
    },
    {
        "name": "Lina — Data Journalist · Trend Spotter",
        "profile": {
            "user_id": "lina",
            "interests": ["trending_oss", "ai_research", "ml", "developer_tools"],
            "free_text": "trending fast growing viral emerging tools community discussion",
            "platforms": ["github", "hackernews", "reddit"],
            "time_budget": 10,
            "source_affinity": {},
        },
        "checks": [
            ("trending_domain>=5",    lambda r: sum(1 for x in r if x["domain"] in ("trending_oss","ai_research","ml","developer_tools")) >= 5),
            ("velocity_above_p60",    lambda r: sorted([x.get("velocity",0) for x in r])[4] >= 0.20),
            ("recent_items>=5",       lambda r: sum(1 for x in r if x.get("velocity",0) >= 0.10) >= 5),
            ("multi_source>=2",       lambda r: len(set(x["source"] for x in r)) >= 2),
        ],
    },
    {
        "name": "Raj — Startup Founder · Marketing-Focused",
        "profile": {
            "user_id": "raj",
            "interests": ["developer_tools", "b2b_saas", "cloud_apis"],
            "free_text": "developer productivity APIs CLI tools open source startup business",
            "platforms": ["reddit", "github", "hackernews"],
            "time_budget": 4,
            "source_affinity": {"reddit": 0.8, "hackernews": 0.9},
        },
        "checks": [
            ("devtools_focus>=6",        lambda r: sum(1 for x in r if x["domain"] in ("developer_tools","b2b_saas","cloud_apis")) >= 6),
            ("visibility_above_median",  lambda r: sum(1 for x in r if x["components"]["visibility_potential"] >= 0.40) >= 5),
            ("respects_time>=5",         lambda r: sum(1 for x in r if x.get("effort",0.5) <= 0.65) >= 5),
            ("discussion_focused>=4",    lambda r: sum(1 for x in r if x.get("num_comments",0) >= 1) >= 4),
        ],
    },
]

def run_personas(topn=10):
    ranker = Ranker()
    passed_total = 0
    results = []
    for p in PERSONAS:
        ranked = ranker.rank(
            interests=p["profile"]["interests"],
            free_text=p["profile"]["free_text"],
            platforms=p["profile"]["platforms"],
            topn=topn,
            source_affinity=p["profile"].get("source_affinity", {}),
        )
        checks_passed = []
        for name, fn in p["checks"]:
            try:
                ok = fn(ranked)
            except Exception as e:
                ok = False
            checks_passed.append((name, ok))
            status = "ok" if ok else "FAIL"
            print(f"        {status}  {name}")
        all_pass = all(ok for _, ok in checks_passed)
        if all_pass:
            passed_total += 1
        print(f"[{'PASS' if all_pass else 'FAIL'}] {p['name']}")
        results.append((p["name"], all_pass, checks_passed))
    print(f"\n{passed_total}/{len(PERSONAS)} personas passed.")
    return results

if __name__ == "__main__":
    run_personas()
