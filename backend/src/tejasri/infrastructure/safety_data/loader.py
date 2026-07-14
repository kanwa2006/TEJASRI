"""Loads the JSON safety dataset into the domain InteractionDataset shape.

The schema is intentionally simple so a full DDInter 2.0 export (or any
richer source) can replace the curated file without code changes. Loaded
once at startup; all lookups are in-memory dict hits — deterministic and
network-free on the hot path.
"""

import json
from functools import lru_cache
from importlib import resources
from typing import Any

from tejasri.domain.safety import Interaction, SafetySeverity

_PACKAGE = "tejasri.infrastructure.safety_data"
_FILENAME = "interactions.json"


class JsonInteractionDataset:
    def __init__(self, raw: dict[str, Any]) -> None:
        self.version: str = raw["version"]
        self._synonyms: dict[str, str] = {k.lower(): v for k, v in raw["synonyms"].items()}
        self._generics: set[str] = {g.lower() for g in raw["generics"]}
        self._interactions: dict[frozenset[str], Interaction] = {}
        for item in raw["interactions"]:
            interaction = Interaction(
                drug_a=item["a"],
                drug_b=item["b"],
                severity=SafetySeverity(item["severity"]),
                description=item["description"],
                source=item["source"],
            )
            self._interactions[frozenset((item["a"], item["b"]))] = interaction
        self._allergies: dict[str, dict[str, Any]] = {
            k.lower(): v for k, v in raw["allergy_cross_sensitivity"].items()
        }

    def normalize(self, drug_name: str) -> str | None:
        name = drug_name.strip().lower()
        if name in self._generics:
            return name
        return self._synonyms.get(name)

    def interaction(self, drug_a: str, drug_b: str) -> Interaction | None:
        return self._interactions.get(frozenset((drug_a, drug_b)))

    def allergy_conflicts(self, drug: str, allergy: str) -> str | None:
        entry = self._allergies.get(allergy.strip().lower())
        if entry is None:
            return None
        if drug in entry["conflicts"]:
            return f"Recorded allergy '{allergy}' contraindicates {drug}. {entry['note']}"
        if drug in entry["possible"]:
            return f"Recorded allergy '{allergy}' may cross-react with {drug}. {entry['note']}"
        return None


@lru_cache
def load_default_dataset() -> JsonInteractionDataset:
    text = resources.files(_PACKAGE).joinpath(_FILENAME).read_text(encoding="utf-8")
    return JsonInteractionDataset(json.loads(text))
