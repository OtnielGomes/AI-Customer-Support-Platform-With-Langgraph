import Link from "next/link";

import { TicketForm } from "@/components/portal/ticket-form";

export default function HomePage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-16">
      <header className="mb-12 flex items-end justify-between gap-6">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">
            Northwind
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-serif)] text-5xl leading-tight">
            How can we help?
          </h1>
          <p className="mt-3 max-w-xl text-[var(--muted)]">
            Open a ticket and our support agents — human and automated — will
            look into billing, shipping, or account issues.
          </p>
        </div>
        <Link
          href="/login"
          className="hidden text-sm text-[var(--muted)] underline-offset-4 hover:underline sm:block"
        >
          Agent login
        </Link>
      </header>
      <section className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6 shadow-[0_20px_60px_-40px_rgba(28,25,21,0.5)]">
        <TicketForm />
      </section>
    </main>
  );
}
