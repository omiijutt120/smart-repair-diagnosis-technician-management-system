from smart_repair.models import DiagnosticRule, DiagnosticResult
from smart_repair.extensions import db


def diagnose(category_id, symptom_ids):
    selected = set(symptom_ids)
    results = []
    rules = DiagnosticRule.query.filter(
        DiagnosticRule.is_active.is_(True), DiagnosticRule.archived_at.is_(None),
        db.or_(DiagnosticRule.category_id == category_id, DiagnosticRule.category_id.is_(None)))
    for rule in rules:
        mappings = [m for m in rule.mappings if not m.archived_at and m.symptom.is_active and not m.symptom.archived_at]
        if not mappings or any(m.is_required and m.symptom_id not in selected for m in mappings):
            continue
        total = sum(m.weight for m in mappings)
        matched = sum(m.weight for m in mappings if m.symptom_id in selected)
        if matched:
            results.append({"rule": rule, "score": round(matched / total * 100, 2),
                            "matched": matched, "total": total,
                            "symptoms": [m.symptom.name for m in mappings if m.symptom_id in selected]})
    return sorted(results, key=lambda r: (-r["score"], -r["rule"].priority, r["rule"].id))[:5]


def save_results(repair_request, results):
    for result in results:
        rule = result["rule"]
        db.session.add(DiagnosticResult(repair_request_id=repair_request.id, rule_id=rule.id,
            result_summary=f"{rule.probable_fault}. {rule.explanation}",
            confidence_score=result["score"], suggested_action=rule.suggested_action))
    if not results:
        db.session.add(DiagnosticResult(repair_request_id=repair_request.id,
            result_summary="No close rule match found — technician inspection required.",
            confidence_score=0, suggested_action="Book a physical inspection at a service centre."))
