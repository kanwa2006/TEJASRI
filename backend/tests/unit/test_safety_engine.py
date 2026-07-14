"""SafetyEngine: deterministic, source-cited, fails toward human review."""

from tejasri.domain.safety import Medication, SafetyEngine, SafetyFlagKind, SafetySeverity
from tejasri.infrastructure.safety_data import load_default_dataset


def engine() -> SafetyEngine:
    return SafetyEngine(load_default_dataset())


def med(name: str) -> Medication:
    return Medication(name=name, dose="1 tab", schedule="daily")


def test_known_major_interaction_is_flagged_with_source() -> None:
    report = engine().check([med("warfarin"), med("ibuprofen")], allergies=[])
    interaction_flags = [f for f in report.flags if f.kind is SafetyFlagKind.INTERACTION]
    assert len(interaction_flags) == 1
    flag = interaction_flags[0]
    assert flag.severity is SafetySeverity.MAJOR
    assert set(flag.drugs) == {"warfarin", "ibuprofen"}
    assert flag.source  # every verdict is citable


def test_brand_names_normalize_to_generics() -> None:
    # Coumadin is warfarin; Advil is ibuprofen — the same major interaction.
    report = engine().check([med("Coumadin"), med("Advil")], allergies=[])
    assert any(f.kind is SafetyFlagKind.INTERACTION for f in report.flags)


def test_contraindicated_pair_is_max_severity() -> None:
    report = engine().check([med("sildenafil"), med("nitroglycerin")], allergies=[])
    assert report.max_severity is SafetySeverity.CONTRAINDICATED


def test_safe_combination_produces_no_flags_but_counts_pairs() -> None:
    report = engine().check([med("metformin"), med("atorvastatin")], allergies=[])
    assert not report.has_flags
    assert report.checked_pairs == 1
    assert report.dataset_version


def test_allergy_conflict_is_contraindicated() -> None:
    report = engine().check([med("amoxicillin")], allergies=["penicillin"])
    allergy_flags = [f for f in report.flags if f.kind is SafetyFlagKind.ALLERGY]
    assert len(allergy_flags) == 1
    assert allergy_flags[0].severity is SafetySeverity.CONTRAINDICATED


def test_allergy_cross_sensitivity_is_surfaced() -> None:
    report = engine().check([med("cephalexin")], allergies=["penicillin"])
    assert any(f.kind is SafetyFlagKind.ALLERGY for f in report.flags)


def test_unknown_drug_demands_human_confirmation_not_false_confidence() -> None:
    report = engine().check([med("obscuremycin")], allergies=[])
    unknown = [f for f in report.flags if f.kind is SafetyFlagKind.UNKNOWN_DRUG]
    assert len(unknown) == 1
    assert unknown[0].needs_confirmation
    assert "obscuremycin" in report.unknown_drugs


def test_engine_is_deterministic() -> None:
    meds = [med("warfarin"), med("aspirin"), med("lisinopril")]
    first = engine().check(meds, allergies=["sulfa"])
    second = engine().check(meds, allergies=["sulfa"])
    assert first == second
