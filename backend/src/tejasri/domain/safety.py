"""Deterministic medication safety (ADR 0004).

The SafetyEngine is pure domain logic over a versioned interaction dataset.
Its verdict is authoritative: the LLM may explain a SafetyReport but can
never add, remove, or reword a severity. Unknown drugs produce an explicit
`needs_confirmation` flag rather than silent false confidence.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class SafetySeverity(StrEnum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CONTRAINDICATED = "contraindicated"


class SafetyFlagKind(StrEnum):
    INTERACTION = "interaction"
    ALLERGY = "allergy"
    UNKNOWN_DRUG = "unknown_drug"


@dataclass(frozen=True, slots=True)
class Medication:
    name: str
    dose: str = ""
    schedule: str = ""
    rxnorm: str | None = None


@dataclass(frozen=True, slots=True)
class Interaction:
    drug_a: str  # normalized (generic, lowercase)
    drug_b: str
    severity: SafetySeverity
    description: str
    source: str  # citation, e.g. "DDInter 2.0" / "openFDA label"


@dataclass(frozen=True, slots=True)
class SafetyFlag:
    kind: SafetyFlagKind
    drugs: tuple[str, ...]
    severity: SafetySeverity | None
    description: str
    source: str
    needs_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class SafetyReport:
    flags: tuple[SafetyFlag, ...]
    checked_pairs: int
    dataset_version: str
    unknown_drugs: tuple[str, ...] = ()

    @property
    def has_flags(self) -> bool:
        return bool(self.flags)

    @property
    def max_severity(self) -> SafetySeverity | None:
        order = list(SafetySeverity)
        severities = [f.severity for f in self.flags if f.severity is not None]
        return max(severities, key=order.index) if severities else None


class InteractionDataset(Protocol):
    """Versioned, deterministic safety knowledge (infrastructure supplies it)."""

    version: str

    def normalize(self, drug_name: str) -> str | None:
        """Map a raw name (brand or generic, any case) to the canonical
        generic name, or None when the drug is not in the dataset."""
        ...

    def interaction(self, drug_a: str, drug_b: str) -> Interaction | None:
        """Interaction between two *normalized* names, order-independent."""
        ...

    def allergy_conflicts(self, drug: str, allergy: str) -> str | None:
        """Non-None explanation when a *normalized* drug conflicts with a
        (raw) recorded allergy, including cross-sensitivity."""
        ...


class SafetyEngine:
    def __init__(self, dataset: InteractionDataset) -> None:
        self._dataset = dataset

    def check(self, medications: list[Medication], allergies: list[str]) -> SafetyReport:
        flags: list[SafetyFlag] = []
        normalized: list[tuple[Medication, str]] = []
        unknown: list[str] = []

        for med in medications:
            canonical = self._dataset.normalize(med.name)
            if canonical is None:
                unknown.append(med.name)
                flags.append(
                    SafetyFlag(
                        kind=SafetyFlagKind.UNKNOWN_DRUG,
                        drugs=(med.name,),
                        severity=None,
                        description=(
                            f"'{med.name}' is not in the safety dataset; interaction "
                            "coverage for it is incomplete and requires human review."
                        ),
                        source=f"dataset {self._dataset.version}",
                        needs_confirmation=True,
                    )
                )
            else:
                normalized.append((med, canonical))

        checked_pairs = 0
        for i, (_, drug_a) in enumerate(normalized):
            for _, drug_b in normalized[i + 1 :]:
                checked_pairs += 1
                interaction = self._dataset.interaction(drug_a, drug_b)
                if interaction is not None:
                    flags.append(
                        SafetyFlag(
                            kind=SafetyFlagKind.INTERACTION,
                            drugs=(interaction.drug_a, interaction.drug_b),
                            severity=interaction.severity,
                            description=interaction.description,
                            source=interaction.source,
                        )
                    )

        for _, drug in normalized:
            for allergy in allergies:
                conflict = self._dataset.allergy_conflicts(drug, allergy)
                if conflict is not None:
                    flags.append(
                        SafetyFlag(
                            kind=SafetyFlagKind.ALLERGY,
                            drugs=(drug,),
                            severity=SafetySeverity.CONTRAINDICATED,
                            description=conflict,
                            source=f"dataset {self._dataset.version}",
                        )
                    )

        return SafetyReport(
            flags=tuple(flags),
            checked_pairs=checked_pairs,
            dataset_version=self._dataset.version,
            unknown_drugs=tuple(unknown),
        )
