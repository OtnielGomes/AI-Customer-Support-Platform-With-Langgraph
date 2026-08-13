import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6">
      <h1 className="font-[family-name:var(--font-serif)] text-4xl">Not found</h1>
      <p className="mt-3 text-[var(--muted)]">That ticket or page does not exist.</p>
      <Link href="/" className="mt-6 text-sm underline">
        Back to the portal
      </Link>
    </main>
  );
}
