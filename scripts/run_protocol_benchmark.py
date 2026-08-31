#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit explicit static protocol coverage; not a live benchmark")
    parser.add_argument("--output", default=str(ROOT / "benchmarks/results.yaml"))
    parser.add_argument("--report", default=str(ROOT / "benchmarks/RESULTS.md"))
    args = parser.parse_args()
    rubric = yaml.safe_load((ROOT / "benchmarks/rubric.yaml").read_text(encoding="utf-8"))
    criteria = rubric["criteria"]
    max_weighted = sum(item["weight"] * 2 for item in criteria.values())
    results = []
    for path in sorted((ROOT / "benchmarks/profiles").glob("*.yaml")):
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        scores = profile["scores"]
        unknown = set(scores) - set(criteria)
        missing = set(criteria) - set(scores)
        if unknown or missing:
            raise SystemExit(f"{path.name}: unknown={sorted(unknown)} missing={sorted(missing)}")
        weighted = sum(criteria[key]["weight"] * int(scores[key]) for key in criteria)
        results.append({
            "name": profile["name"],
            "profile": str(path.relative_to(ROOT)),
            "weighted_score": weighted,
            "max_weighted_score": max_weighted,
            "coverage_percent": round(weighted / max_weighted * 100, 1),
            "notes": profile.get("notes", ""),
        })
    results.sort(key=lambda item: (-item["weighted_score"], item["name"]))
    scenario_config = yaml.safe_load((ROOT / "benchmarks/scenarios.yaml").read_text(encoding="utf-8"))
    profiles_by_name = {}
    for path in sorted((ROOT / "benchmarks/profiles").glob("*.yaml")):
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        profiles_by_name[profile["name"]] = profile["scores"]
    scenario_results = {}
    for scenario_id, config in scenario_config["scenarios"].items():
        keys = config["criteria"]
        maximum = sum(criteria[key]["weight"] * 2 for key in keys)
        ranking = []
        for name, scores in profiles_by_name.items():
            weighted = sum(criteria[key]["weight"] * int(scores[key]) for key in keys)
            ranking.append({"name": name, "score": weighted, "maximum": maximum, "coverage_percent": round(weighted / maximum * 100, 1)})
        ranking.sort(key=lambda item: (-item["score"], item["name"]))
        scenario_results[scenario_id] = {"description": config["description"], "ranking": ranking}
    output = {
        "schema_version": "1.0",
        "audit_type": rubric.get("audit_type", rubric.get("benchmark_type", "static_protocol_coverage")),
        "warning": rubric["warning"],
        "ranking": results,
        "scenario_results": scenario_results,
    }
    out = Path(args.output)
    out.write_text(yaml.safe_dump(output, sort_keys=False, allow_unicode=True), encoding="utf-8")
    report_lines = [
        "# Static Protocol Coverage Audit",
        "",
        "> Static source-contract comparison. This does not prove live model superiority.",
        "",
        "| Rank | System | Weighted score | Coverage |",
        "|---:|---|---:|---:|",
    ]
    for index, item in enumerate(results, 1):
        report_lines.append(f"| {index} | {item['name']} | {item['weighted_score']}/{max_weighted} | {item['coverage_percent']}% |")
    report_lines.extend(["", "## Scenario leaders", ""])
    for scenario_id, scenario in scenario_results.items():
        top_score = scenario["ranking"][0]["score"]
        leaders = [item["name"] for item in scenario["ranking"] if item["score"] == top_score]
        report_lines.append(f"- **{scenario_id}**: {', '.join(leaders)} — {scenario['description']}")
    report_lines.extend(["", "## Interpretation", "", "A higher score means the reviewed source explicitly operationalizes more benchmark capabilities. Live interview quality, model behavior, installation quality, and user satisfaction require separate evaluation.", ""])
    Path(args.report).write_text("\n".join(report_lines), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {args.report}")
    for index, item in enumerate(results, 1):
        print(f"{index}. {item['name']}: {item['weighted_score']}/{max_weighted} ({item['coverage_percent']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
