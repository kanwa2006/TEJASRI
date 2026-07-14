/** Renders the deterministic safety verdict — always with severity + source. */

import type { SafetyReport } from "../lib/types";
import { Badge } from "./ui";

export default function SafetyReportView({ report }: { report: SafetyReport }) {
  if (!report.flags.length) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-ok/5 p-3 text-sm text-ink-soft">
        <Badge tone="ok">clear</Badge>
        No interactions or allergy conflicts across {report.checked_pairs} checked pair
        {report.checked_pairs === 1 ? "" : "s"} · dataset {report.dataset_version}
      </div>
    );
  }
  return (
    <ul className="space-y-2">
      {report.flags.map((flag, i) => (
        <li
          key={i}
          className="rounded-lg border border-line bg-surface-2/60 p-3 text-sm"
        >
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <Badge tone={flag.severity ?? "review"}>{flag.severity ?? "review"}</Badge>
            <span className="font-medium text-ink">{flag.drugs.join(" + ")}</span>
            {flag.needs_confirmation && <Badge tone="review">needs confirmation</Badge>}
          </div>
          <p className="text-ink-soft">{flag.description}</p>
          <p className="mt-1 text-xs text-ink-soft/80">Source: {flag.source}</p>
        </li>
      ))}
    </ul>
  );
}
