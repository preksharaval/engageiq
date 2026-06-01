"""
GitHub ingestion — pulls issues, PRs, and repos across all 15 domains.
Writes progressively to data/raw/github.jsonl after each domain.
"""
import os, json, time, yaml, requests
from pathlib import Path

TOKEN   = os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("Set GITHUB_TOKEN in your environment (do not hardcode it).")
ROOT    = Path(__file__).resolve().parent.parent.parent
RAW     = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
OUT     = RAW / "github.jsonl"
HEADERS = {"Authorization": f"token {TOKEN}",
           "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28"}

def gh(url, params=None):
    for _ in range(3):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=15)
            if r.status_code == 403:
                reset = int(r.headers.get("X-RateLimit-Reset", time.time()+60))
                time.sleep(max(reset - time.time(), 1))
                continue
            if r.status_code == 200:
                return r.json()
        except Exception: pass
        time.sleep(2)
    return None

def remaining():
    d = gh("https://api.github.com/rate_limit")
    return d["rate"]["remaining"] if d else 0

def fetch_issues(query, domain_key, pages=2, per_page=50):
    recs, seen = [], set()
    for page in range(1, pages+1):
        data = gh("https://api.github.com/search/issues",
                  {"q": query+" is:open", "sort":"reactions",
                   "order":"desc", "per_page":per_page, "page":page})
        if not data: break
        for item in (data.get("items") or []):
            if item["html_url"] in seen: continue
            seen.add(item["html_url"])
            labels = [l["name"].lower() for l in item.get("labels",[])]
            gfi = any("good first" in l or "beginner" in l or "hacktoberfest" in l for l in labels)
            recs.append({"source":"github","domain":domain_key,
                "opp_type":"pr" if item.get("pull_request") else "issue",
                "title":item["title"],
                "body":(item.get("body") or "")[:400],
                "url":item["html_url"],"author":item.get("user",{}).get("login",""),
                "created_at":item["created_at"],
                "score_raw":item.get("reactions",{}).get("total_count",0),
                "num_comments":item.get("comments",0),
                "velocity":float(item.get("comments",0)),
                "community_size":0,"effort":0.3 if gfi else 0.6,
                "tags":labels[:5],"good_first_issue":gfi})
        time.sleep(0.5)
    return recs

def fetch_repos(query, domain_key, pages=2, per_page=50):
    recs, seen = [], set()
    for page in range(1, pages+1):
        data = gh("https://api.github.com/search/repositories",
                  {"q":query,"sort":"stars","order":"desc",
                   "per_page":per_page,"page":page})
        if not data: break
        for repo in (data.get("items") or []):
            if repo["html_url"] in seen: continue
            seen.add(repo["html_url"])
            gfi = repo.get("open_issues_count",0) > 0
            topics = repo.get("topics") or []
            recs.append({"source":"github","domain":domain_key,
                "opp_type":"repo",
                "title":repo["full_name"]+" — "+(repo.get("description") or ""),
                "body":(repo.get("description") or "")[:400],
                "url":repo["html_url"],"author":repo.get("owner",{}).get("login",""),
                "created_at":repo.get("pushed_at") or repo["created_at"],
                "score_raw":repo.get("stargazers_count",0),
                "num_comments":repo.get("open_issues_count",0),
                "velocity":float(repo.get("stargazers_count",0))/max(1,30),
                "community_size":repo.get("stargazers_count",0),
                "effort":0.3 if gfi else 0.5,
                "tags":topics[:5],"good_first_issue":gfi,
                "forks":repo.get("forks_count",0),
                "contributors_approx":max(1,repo.get("forks_count",1))})
        time.sleep(0.5)
    return recs

QUERIES = {
    "ml":              [("machine-learning label:\"good first issue\" language:python","issue"),
                        ("topic:machine-learning stars:>50","repo")],
    "devops_k8s":      [("topic:kubernetes stars:>100","repo"),
                        ("topic:terraform stars:>50","repo")],
    "trending_oss":    [("stars:>500 pushed:>2026-03-01 language:python","repo"),
                        ("stars:>500 pushed:>2026-03-01 language:javascript","repo")],
    "developer_tools": [("topic:developer-tools stars:>30","repo"),
                        ("label:\"good first issue\" topic:cli","issue")],
    "cybersecurity":   [("topic:security stars:>50","repo"),
                        ("topic:cybersecurity","issue")],
    "frontend_web":    [("topic:react label:\"good first issue\"","issue"),
                        ("topic:nextjs stars:>100","repo")],
    "b2b_saas":        [("topic:saas stars:>20","repo"),
                        ("topic:api-platform","repo")],
    "blockchain":      [("topic:solidity stars:>30","repo"),
                        ("topic:blockchain label:\"good first issue\"","issue")],
    "python_data_eng": [("topic:dbt stars:>50","repo"),
                        ("topic:data-pipeline language:python","repo")],
    "gamedev_cpp":     [("topic:game-engine language:cpp","repo"),
                        ("topic:godot","repo")],
    "ai_research":     [("topic:llm stars:>100","repo"),
                        ("topic:rag label:\"good first issue\"","issue")],
    "embedded_systems":[("topic:embedded language:c","repo"),
                        ("topic:arduino stars:>30","repo")],
    "cloud_apis":      [("topic:serverless stars:>50","repo"),
                        ("topic:aws-lambda","issue")],
    "mobile_dev":      [("topic:flutter label:\"good first issue\"","issue"),
                        ("topic:swiftui","repo")],
    "beginner_coding": [("label:\"good first issue\" language:python stars:>20","issue"),
                        ("topic:hacktoberfest","repo")],
}

def main():
    written = 0
    with open(OUT, "w") as f:
        for domain_key, queries in QUERIES.items():
            print(f"[{domain_key}] ({remaining()} calls left)", flush=True)
            seen, domain_recs = set(), []
            for query, qtype in queries:
                fn = fetch_issues if qtype=="issue" else fetch_repos
                recs = fn(query, domain_key)
                for r in recs:
                    if r["url"] not in seen:
                        seen.add(r["url"])
                        domain_recs.append(r)
                print(f"  {qtype} '{query[:45]}' -> {len(recs)}", flush=True)
            for r in domain_recs:
                f.write(json.dumps(r)+"\n")
            written += len(domain_recs)
            print(f"  => {len(domain_recs)} unique  (total so far: {written})", flush=True)
    print(f"\nDone. {written} records -> {OUT}")

if __name__ == "__main__":
    main()
