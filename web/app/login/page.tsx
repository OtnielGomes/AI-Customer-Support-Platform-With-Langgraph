import { LoginForm } from "@/components/console/login-form";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const params = await searchParams;
  const nextPath = params.next && params.next.startsWith("/") ? params.next : "/console/tickets";

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Northwind</p>
      <h1 className="mt-2 font-[family-name:var(--font-serif)] text-4xl">Support console</h1>
      <p className="mt-2 mb-8 text-[var(--muted)]">
        Agents sign in here to work the queue, inspect traces, and reply to
        escalations.
      </p>
      <LoginForm nextPath={nextPath} />
    </main>
  );
}
