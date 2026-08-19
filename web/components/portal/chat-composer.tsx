"use client";

export function ChatComposer({
  disabled,
  placeholder,
  onSend,
  variant = "portal",
}: {
  disabled: boolean;
  placeholder: string;
  onSend: (content: string) => void;
  variant?: "portal" | "console";
}) {
  const fieldClass =
    variant === "console"
      ? "rounded-xl border border-white/15 bg-[#0f1216] px-3 py-2 text-[#f2efe9] placeholder:text-[#8b939c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/40"
      : "rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-[var(--ink)] placeholder:text-[var(--muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

  return (
    <form
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const field = form.elements.namedItem("content") as HTMLTextAreaElement;
        const value = field.value.trim();
        if (!value) {
          return;
        }
        onSend(value);
        field.value = "";
      }}
    >
      <textarea
        name="content"
        rows={3}
        placeholder={placeholder}
        disabled={disabled}
        className={fieldClass}
      />
      <button
        type="submit"
        disabled={disabled}
        className="justify-self-start rounded-full bg-[var(--accent)] px-5 py-2.5 text-sm font-medium text-[var(--accent-ink)] disabled:opacity-60"
      >
        {disabled ? "Enviando…" : "Enviar"}
      </button>
    </form>
  );
}
