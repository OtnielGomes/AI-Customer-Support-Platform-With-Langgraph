export function TypingIndicator({
  visible,
  variant = "portal",
}: {
  visible: boolean;
  variant?: "portal" | "console";
}) {
  if (!visible) {
    return null;
  }
  const tone = variant === "console" ? "text-[#9aa3ad]" : "text-[var(--muted)]";
  return <p className={`text-sm ${tone}`}>O assistente está escrevendo…</p>;
}
