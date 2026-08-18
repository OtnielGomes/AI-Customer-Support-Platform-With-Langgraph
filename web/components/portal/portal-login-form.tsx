"use client";

import { useState } from "react";

import { portalLoginAction } from "@/app/portal/actions";

export function PortalLoginForm() {
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="grid gap-4"
      action={async (formData) => {
        const result = await portalLoginAction(formData);
        if (result?.error) {
          setError(result.error);
        }
      }}
    >
      <label className="grid gap-1 text-sm">
        <span className="font-medium">E-mail da conta</span>
        <input
          type="email"
          name="email"
          required
          autoComplete="email"
          placeholder="ana.costa@nexamail.com"
          className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
        />
      </label>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <button
        type="submit"
        className="rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-ink)]"
      >
        Entrar no suporte
      </button>
    </form>
  );
}
