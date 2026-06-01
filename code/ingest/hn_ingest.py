"""
Hacker News ingestion via Algolia API — no auth required.
Writes to data/raw/hackernews.jsonl
"""
import json, time, requests, yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent.parent
RAW  = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
OUT  = RAW / "hackernews.jsonl"

ALGOLIA = "https://hn.algolia.com/api/v1/search"

def search_hn(query, domain_key, tags="story", max_pages=5, per_page=50):
    records = []
    seen = set()
    # search last 90 days
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
    for page in range(max_pages):
        try:
            r = requests.get(ALGOLIA, params={
                "query": query, "tags": tags,
                "hitsPerPage": per_page, "page": page,
                "numericFilters": f"created_at_i>{cutoff},points>2",
            }, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            hits = data.get("hits", [])
            if not hits:
                break
            for h in hits:
                url = h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}"
                if url in seen:
                    continue
                seen.add(url)
                pts = h.get("points", 1) or 1
                cmts = h.get("num_comments", 0) or 0
                records.append({
                    "source": "hackernews",
                    "domain": domain_key,
                    "opp_type": "show" if "Show HN" in (h.get("title") or "") else "story",
                    "title": h.get("title", ""),
                    "body": (h.get("story_text") or "")[:500],
                    "url": url,
                    "author": h.get("author", ""),
                    "created_at": datetime.fromtimestamp(
                        h["created_at_i"], tz=timezone.utc).isoformat(),
                    "score_raw": pts,
                    "num_comments": cmts,
                    "velocity": float(pts + cmts * 2),
                    "community_size": 500000,
                    "effort": 0.4,
                    "tags": [],
                    "good_first_issue": False,
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"  HN error: {e}")
            break
    return records

def main():
    cfg = yaml.safe_load(open(ROOT / "code" / "domains.yaml"))["domains"]
    all_records = []

    hn_queries = {
        "ml":               ["pytorch machine learning", "scikit-learn tutorial", "mlflow experiment"],
        "devops_k8s":       ["kubernetes deployment", "terraform infrastructure", "helm charts ci/cd"],
        "trending_oss":     ["Show HN open source", "new open source project", "github trending"],
        "developer_tools":  ["developer tools cli", "vscode extension", "language server protocol"],
        "cybersecurity":    ["security vulnerability CVE", "supply chain attack", "application security"],
        "frontend_web":     ["react nextjs frontend", "tailwind css", "svelte typescript"],
        "b2b_saas":         ["SaaS product api", "developer api platform", "product led growth"],
        "blockchain":       ["ethereum smart contract", "zero knowledge proof", "defi protocol"],
        "python_data_eng":  ["airflow data pipeline", "dbt analytics", "apache spark python"],
        "gamedev_cpp":      ["godot game engine", "unreal engine cpp", "game development opengl"],
        "ai_research":      ["large language model", "RAG retrieval augmented", "transformer architecture"],
        "embedded_systems": ["embedded systems rtos", "firmware arduino", "microcontroller bare metal"],
        "cloud_apis":       ["aws lambda serverless", "google cloud run", "api gateway"],
        "mobile_dev":       ["flutter mobile app", "swiftui ios", "android jetpack compose"],
        "beginner_coding":  ["learn programming beginner", "good first issue contribution", "open source first PR"],
    }

    for domain_key, queries in hn_queries.items():
        domain_records = []
        for q in queries:
            recs = search_hn(q, domain_key)
            domain_records.extend(recs)
            time.sleep(1)
        # dedupe
        seen = set()
        for r in domain_records:
            if r["url"] not in seen:
                seen.add(r["url"])
                all_records.append(r)
        print(f"[{domain_key}] {len(seen)} unique HN records")

    with open(OUT, "w") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(all_records)} HN records to {OUT}")

if __name__ == "__main__":
    main()
