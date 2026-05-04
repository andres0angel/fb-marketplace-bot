"""
Persistencia simple de anuncios ya vistos usando JSON.
"""

import json
import os
from datetime import datetime

DB_FILE = os.environ.get("DB_FILE", "seen_ads.json")


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {"seen_ids": [], "ads": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_seen(ad_id: str) -> bool:
    data = _load()
    return ad_id in data["seen_ids"]


def mark_seen(ad: dict):
    data = _load()
    if ad["id"] not in data["seen_ids"]:
        data["seen_ids"].append(ad["id"])
        ad["seen_at"] = datetime.now().isoformat()
        data["ads"].append(ad)
        # Mantener solo los últimos 500 para no crecer infinito
        if len(data["seen_ids"]) > 500:
            data["seen_ids"] = data["seen_ids"][-500:]
            data["ads"] = data["ads"][-500:]
        _save(data)


def get_all_ads() -> list:
    return _load().get("ads", [])


def clear_db():
    _save({"seen_ids": [], "ads": []})
