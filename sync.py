#!/usr/bin/env python3
"""
Sync Vietnamese IME repositories metadata from GitHub API using repos.yml as source of truth.
Includes a persistent snapshot cache (cache.json) to preserve metadata if a repo is deleted (404)
or if the GitHub API encounters network/rate limit issues.

Outputs:
  - cache.json (persistent metadata snapshot)
  - data.json (consumed by the static web dashboard)
  - bo-go-tieng-viet.csv (generated export for spreadsheet users)
"""

import csv
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
import yaml

INPUT_YAML = "repos.yml"
CACHE_FILE = "cache.json"
OUTPUT_CSV = "bo-go-tieng-viet.csv"
OUTPUT_JSON = "data.json"


def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        try:
            token = subprocess.check_output(
                ["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            token = ""
    return token


def parse_repo_owner_name(url: str):
    url = url.strip().rstrip("/")
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def fetch_repo_meta(owner: str, repo: str, token: str):
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "User-Agent": "Vietnamese-IME-Tracker",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "Not Found", "status_code": 404}
        print(f"[WARN] HTTP {e.code} for {owner}/{repo}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[ERROR] Failed fetching {owner}/{repo}: {e}", file=sys.stderr)
        return None


def calculate_status(archived: bool, is_deleted: bool, pushed_raw: str, now_utc: datetime):
    """
    Transparent Activity Criteria:
    - Dead: Deleted/404, Archived by owner, or no commits for > 365 days (> 1 year)
    - Inactive: Not archived, pushed between 181 and 365 days ago (6 to 12 months)
    - Active: Not archived, pushed within <= 180 days (<= 6 months)
    """
    if is_deleted or archived:
        return "Dead", None

    if not pushed_raw:
        return "Inactive", None

    try:
        pushed_dt = datetime.fromisoformat(pushed_raw.replace("Z", "+00:00"))
        days_diff = (now_utc - pushed_dt).days
        if days_diff <= 180:
            return "Active", days_diff
        elif days_diff <= 365:
            return "Inactive", days_diff
        else:
            return "Dead", days_diff
    except Exception:
        return "Inactive", None


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not read {CACHE_FILE}: {e}", file=sys.stderr)
    return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"[OK] Saved snapshot {CACHE_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save {CACHE_FILE}: {e}", file=sys.stderr)


def main():
    if not os.path.exists(INPUT_YAML):
        print(f"Error: {INPUT_YAML} not found.", file=sys.stderr)
        sys.exit(1)

    token = get_github_token()
    if token:
        print("[INFO] GitHub Token found (rate limit: 5,000 req/hr).")
    else:
        print("[WARN] No GitHub Token found (unauthenticated rate limit: 60 req/hr).")

    with open(INPUT_YAML, mode="r", encoding="utf-8") as f:
        entries = yaml.safe_load(f) or []

    cache = load_cache()
    print(f"[INFO] Loaded {len(entries)} repositories (Snapshot cache entries: {len(cache)})...")

    now_utc = datetime.now(timezone.utc)
    csv_rows = []
    items_for_json = []

    for entry in entries:
        name = str(entry.get("name", "")).strip()
        url = str(entry.get("url", "")).strip()
        framework = str(entry.get("framework", "Standalone (Wayland)")).strip()
        maintainer = str(entry.get("maintainer", "")).strip()
        os_platform = str(entry.get("os", "Linux")).strip()
        explicit_license = str(entry.get("license", "")).strip()

        owner, repo_name = parse_repo_owner_name(url)

        # Retrieve cached baseline if available
        cached = cache.get(url, {})
        stars = cached.get("stars", 0)
        language = cached.get("language", "")
        license_str = explicit_license or cached.get("license", "")
        created = cached.get("created", "")
        last_update = cached.get("last_update", "")
        description = cached.get("description", "")
        archived = cached.get("archived", False)
        deleted = cached.get("deleted", False)

        days_since_push = None
        status = "Active"

        if owner and repo_name:
            print(f"  -> Fetching {owner}/{repo_name}...", end=" ", flush=True)
            meta = fetch_repo_meta(owner, repo_name, token)

            if meta and "error" in meta and meta.get("status_code") == 404:
                print("DELETED/404 (restored from cache)")
                deleted = True
                status = "Dead"
                # Keep cached stars, language, license, created, last_update
            elif meta:
                deleted = False
                archived = meta.get("archived", False)
                stars = meta.get("stargazers_count", stars)
                description = meta.get("description") or description

                api_lang = meta.get("language")
                if api_lang:
                    language = api_lang

                if not license_str:
                    lic = meta.get("license")
                    if lic and isinstance(lic, dict):
                        spdx = lic.get("spdx_id")
                        if spdx and spdx != "NOASSERTION":
                            license_str = spdx

                created_raw = meta.get("created_at")
                if created_raw:
                    created = created_raw.split("T")[0]

                pushed_raw = meta.get("pushed_at")
                if pushed_raw:
                    last_update = pushed_raw.split("T")[0]

                status, days_since_push = calculate_status(archived, deleted, pushed_raw, now_utc)

                status_emoji = "🟢" if status == "Active" else ("🟡" if status == "Inactive" else "🔴")
                days_msg = f"{days_since_push}d ago" if days_since_push is not None else "archived"
                print(f"OK ({status_emoji} {status} [{days_msg}], ⭐ {stars}, lang: {language})")
            else:
                print("FETCH ERROR (using cached values)")
                status, days_since_push = calculate_status(archived, deleted, last_update, now_utc)
        else:
            status, days_since_push = calculate_status(archived, deleted, last_update, now_utc)

        # Update cache for this URL
        cache[url] = {
            "stars": stars,
            "language": language,
            "license": license_str,
            "created": created,
            "last_update": last_update,
            "description": description,
            "archived": archived,
            "deleted": deleted,
            "last_synced": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        # Calculate relative days if last_update exists but not calculated
        if days_since_push is None and last_update:
            try:
                dt = datetime.strptime(last_update, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_since_push = (now_utc - dt).days
            except Exception:
                pass

        csv_rows.append({
            "Status": status,
            "Repo Name": name,
            "GitHub URL": url,
            "Framework": framework,
            "Maintainer": maintainer,
            "Language": language,
            "Stars": str(stars),
            "License": license_str,
            "Last Update": last_update,
            "Created": created,
            "OS": os_platform,
        })

        items_for_json.append({
            "name": name,
            "repo": f"{owner}/{repo_name}" if owner and repo_name else name,
            "url": url,
            "framework": framework,
            "maintainer": maintainer,
            "status": status,
            "deleted": deleted,
            "days_since_push": days_since_push,
            "created": created,
            "last_update": last_update,
            "stars": stars,
            "language": language,
            "license": license_str,
            "os": os_platform,
            "description": description,
            "archived": archived,
        })

    # Save updated cache
    save_cache(cache)

    # Sort JSON items: Active first, then Inactive, then Dead, and by Stars descending
    status_weights = {"Active": 0, "Inactive": 1, "Dead": 2}
    items_for_json.sort(key=lambda x: (status_weights.get(x["status"], 3), -x["stars"], x["name"].lower()))

    # Sort CSV rows identically
    csv_rows.sort(
        key=lambda r: (
            status_weights.get(r.get("Status", ""), 3),
            -(int(r.get("Stars")) if r.get("Stars", "").isdigit() else 0),
            r.get("Repo Name", "").lower(),
        )
    )

    # Export generated CSV
    with open(OUTPUT_CSV, mode="w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "Status",
            "Repo Name",
            "GitHub URL",
            "Framework",
            "Maintainer",
            "Language",
            "Stars",
            "License",
            "Last Update",
            "Created",
            "OS",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[OK] Exported {OUTPUT_CSV}")

    # Export JSON for Static Web Dashboard
    payload = {
        "updated_at": now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_repos": len(items_for_json),
        "repos": items_for_json,
    }
    with open(OUTPUT_JSON, mode="w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Exported {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
