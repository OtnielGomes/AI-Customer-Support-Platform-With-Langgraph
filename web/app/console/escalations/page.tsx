import { EscalationQueue } from "@/components/console/escalation-queue";

export default function EscalationsPage() {
  return (
    <div className="grid gap-6">
      <header>
        <h1 className="font-[family-name:var(--font-serif)] text-3xl text-white">
          Human Escalation
        </h1>
        <p className="mt-1 text-sm text-[#9aa3ad]">
          Oldest waiting tickets first. A reply resumes the paused graph.
        </p>
      </header>
      <EscalationQueue />
    </div>
  );
}
