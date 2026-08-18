export function TypingIndicator({ visible }: { visible: boolean }) {
  if (!visible) {
    return null;
  }
  return <p className="text-sm text-[var(--muted)]">O assistente está escrevendo…</p>;
}
