"use client";

export function ChatComposer({
  disabled,
  placeholder,
  onSend,
}: {
  disabled: boolean;
  placeholder: string;
  onSend: (content: string) => void;
}) {
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
        className="rounded-xl border border-[var(--line)] bg-white px-3 py-2"
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
