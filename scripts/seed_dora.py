#!/usr/bin/env python
"""Seed DORA metrics data via the metrics service API.

Usage:
    python scripts/seed_dora.py [BASE_URL]

Default BASE_URL: http://k8s-workflow-workflow-40cd3e1fe4-525208112.ap-southeast-1.elb.amazonaws.com
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_BASE = (
    "http://k8s-workflow-workflow-40cd3e1fe4-525208112.ap-southeast-1.elb.amazonaws.com"
)
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
REPO = "SilkLee/workflow-ai"
DAYS = 21  # 3 weeks of data
DEPLOYS_PER_DAY_RANGE = (1, 3)  # 1-3 deploys per day (high performer)
INCIDENT_PROBABILITY = 0.10  # ~10% of deploys cause an incident
LEAD_TIME_HOURS_RANGE = (4, 24)  # hours from first commit to deploy
MTTR_HOURS_RANGE = (1, 6)  # hours to resolve incident

random.seed(42)  # deterministic for reproducibility


def _sha(day: int, idx: int) -> str:
    """Generate a realistic-looking commit SHA."""
    raw = f"seed-{day}-{idx}"
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def _post(path: str, body: dict) -> dict:
    """POST JSON to the metrics API via the API Gateway."""
    url = f"{BASE_URL}/api{path}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"  ERROR {path}: {exc}")
        return {}


def _get(path: str) -> dict:
    """GET from the metrics API."""
    url = f"{BASE_URL}/api{path}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        print(f"  ERROR {path}: {exc}")
        return {}


def main() -> None:
    print(f"Seeding DORA metrics data to {BASE_URL}")
    print(f"  Repository: {REPO}")
    print(f"  Period: last {DAYS} days")
    print()

    now = datetime.now(timezone.utc)
    deploy_count = 0
    change_count = 0
    incident_count = 0

    for day_offset in range(DAYS, 0, -1):
        base_day = now - timedelta(days=day_offset)
        num_deploys = random.randint(*DEPLOYS_PER_DAY_RANGE)

        for idx in range(num_deploys):
            sha = _sha(day_offset, idx)

            # Spread deploys across business hours (9-18 UTC)
            hour = random.randint(9, 17)
            minute = random.randint(0, 59)
            deployed_at = base_day.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            # Deployment success: ~90% success rate
            success = random.random() > INCIDENT_PROBABILITY

            # Record deployment
            resp = _post(
                "/metrics/events/deployment",
                {
                    "repo": REPO,
                    "sha": sha,
                    "deployed_at": deployed_at.isoformat(),
                    "success": success,
                },
            )
            if resp.get("id"):
                deploy_count += 1

            # Record change (lead time)
            lead_hours = random.uniform(*LEAD_TIME_HOURS_RANGE)
            first_commit_at = deployed_at - timedelta(hours=lead_hours)
            merged_at = deployed_at - timedelta(
                hours=random.uniform(0.5, min(2.0, lead_hours))
            )

            resp = _post(
                "/metrics/events/change",
                {
                    "repo": REPO,
                    "sha": sha,
                    "first_commit_at": first_commit_at.isoformat(),
                    "merged_at": merged_at.isoformat(),
                    "deployed_at": deployed_at.isoformat(),
                },
            )
            if resp.get("id"):
                change_count += 1

            # Occasionally record an incident
            if not success:
                detected_at = deployed_at + timedelta(minutes=random.randint(5, 30))
                mttr_hours = random.uniform(*MTTR_HOURS_RANGE)
                resolved_at = detected_at + timedelta(hours=mttr_hours)

                resp = _post(
                    "/metrics/events/incident",
                    {
                        "repo": REPO,
                        "detected_at": detected_at.isoformat(),
                        "resolved_at": resolved_at.isoformat(),
                        "caused_by_sha": sha,
                        "severity": random.choice(["low", "medium", "medium", "high"]),
                    },
                )
                if resp.get("id"):
                    incident_count += 1

    print(
        f"Seeded {deploy_count} deployments, {change_count} changes, "
        f"{incident_count} incidents"
    )
    print()

    # Verify: fetch DORA metrics
    print("Verifying DORA metrics...")
    dora = _get("/metrics/dora?repo=" + REPO)
    if dora:
        print(
            f"  Deployment Frequency: {dora.get('deployment_frequency', 'N/A'):.2f} /day"
        )
        print(f"  Lead Time:            {dora.get('lead_time', 'N/A'):.1f} hours")
        print(f"  Change Failure Rate:  {dora.get('change_failure_rate', 'N/A'):.1%}")
        print(f"  MTTR:                 {dora.get('mttr', 'N/A'):.1f} hours")
        print(f"  Level:                {dora.get('level', 'N/A')}")
        trend = dora.get("trend", [])
        print(f"  Trend points:         {len(trend)}")
    else:
        print("  WARNING: Could not fetch DORA metrics. Service may be unreachable.")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
