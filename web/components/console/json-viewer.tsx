"use client";

import { useState } from "react";

export function JsonViewer({ value }: { value: unknown }) {
  const [open, setOpen] = useState(false);
  const text = JSON.stringify(value, null, 2) ?? "null";
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="text-xs text-[#9aa3ad] hover:text-white"
      >
        {open ? "Hide JSON" : "Show JSON"}
      </button>
      {open ? (
        <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-black/40 p-3 text-xs text-[#d7dee6]">
          {text}
        </pre>
      ) : null}
    </div>
  );
}
