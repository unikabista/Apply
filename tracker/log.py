import csv
import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "applications-log.csv")

FIELDNAMES = ["date", "company", "role", "ats", "url", "status", "pay", "tier", "notes"]

STATUS_SUBMITTED    = "submitted"
STATUS_REJECTED     = "REJECTED"
STATUS_BLOCKED      = "BLOCKED"
STATUS_CLOSED       = "CLOSED"
STATUS_SKIPPED      = "SKIPPED"
STATUS_PENDING      = "PENDING"
STATUS_OUTREACH     = "OUTREACH SENT"
STATUS_INTERVIEW    = "INTERVIEW"
STATUS_ERROR        = "ERROR"


def _init():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()


def log(company: str, role: str, ats: str, url: str, status: str,
        pay: str = "", tier: str = "", notes: str = ""):
    _init()
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=FIELDNAMES).writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "company": company,
            "role": role,
            "ats": ats,
            "url": url,
            "status": status,
            "pay": pay,
            "tier": tier,
            "notes": notes,
        })


def already_applied(company: str) -> bool:
    """Return True if we have a non-skipped/closed entry for this company."""
    if not os.path.exists(LOG_FILE):
        return False
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["company"].strip().lower() == company.strip().lower()
                    and row["status"] not in (STATUS_SKIPPED, STATUS_CLOSED, "DRY_RUN", STATUS_ERROR)):
                return True
    return False


def get_all() -> list:
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summary() -> dict:
    rows = get_all()
    counts = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts
