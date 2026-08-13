"use client";

import { useState } from "react";

import { loginAction } from "@/app/console/actions";

export function LoginForm({ nextPath }: { nextPath: string }) {
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="grid gap-4"
      action={async (formData) => {
        const result = await loginAction(formData);
        if (result?.error) {
          setError(result.error);
        }
      }}
    >
      <input type="hidden" name="next" value={nextPath} />
      <label className="grid gap-1 text-sm">
        <span className="font-medium">Password</span>
        <input
          type="password"
          name="password"
          required
          className="rounded-lg border border-[var(--line)] bg-white px-3 py-2"
        />
      </label>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <button
        type="submit"
        className="rounded-full bg-[#1c1915] px-5 py-2.5 text-sm font-medium text-[#fff7ef]"
      >
        Enter console
      </button>
    </form>
  );
}
