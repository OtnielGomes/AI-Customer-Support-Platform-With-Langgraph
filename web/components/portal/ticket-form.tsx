"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

export function TicketForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(null);
    startTransition(async () => {
      const response = await fetch("/api/support/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          customer_email: form.get("customer_email"),
          customer_name: form.get("customer_name"),
          subject: form.get("subject"),
          description: form.get("description"),
        }),
      });
      if (!response.ok) {
        setError((await response.text()) || "Could not create ticket.");
        return;
      }
      const ticket = (await response.json()) as { id: string };
      router.push(`/tickets/${ticket.id}`);
    });
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="font-medium">Name</span>
          <input
            required
            name="customer_name"
            className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
            placeholder="Ada Lovelace"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-medium">Email</span>
          <input
            required
            type="email"
            name="customer_email"
            className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
            placeholder="ada@example.com"
          />
        </label>
      </div>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">Subject</span>
        <input
          required
          name="subject"
          className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
          placeholder="Charge on invoice INV-1001"
        />
      </label>
      <label className="grid gap-1 text-sm">
        <span className="font-medium">How can we help?</span>
        <textarea
          required
          name="description"
          rows={6}
          className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
          placeholder="Describe the issue. Include invoice IDs, order numbers, or account details when you have them."
        />
      </label>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <button
        type="submit"
        disabled={pending}
        className="justify-self-start rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-ink)] disabled:opacity-60"
      >
        {pending ? "Opening ticket…" : "Submit ticket"}
      </button>
    </form>
  );
}
