from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pt_web_gap_finder.models import CompanyLead


def write_leads_json(leads: Iterable[CompanyLead], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [lead.model_dump(mode="json") for lead in leads]
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_evidence_jsonl(leads: Iterable[CompanyLead], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for lead in leads:
            for evidence in lead.evidence:
                item = evidence.model_dump(mode="json")
                item["lead_id"] = lead.id
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
