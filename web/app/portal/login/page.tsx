import Link from "next/link";

import { PortalLoginForm } from "@/components/portal/portal-login-form";

export default function PortalLoginPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">TechStore Support</p>
      <h1 className="mt-2 font-[family-name:var(--font-serif)] text-4xl">Suporte ao cliente</h1>
      <p className="mt-2 mb-8 text-[var(--muted)]">
        Entre com o e-mail da sua conta. Vamos reconhecer seus pedidos automaticamente.
      </p>
      <PortalLoginForm />
      <Link href="/login" className="mt-8 text-sm text-[var(--muted)] hover:underline">
        Acesso da equipe de suporte
      </Link>
    </main>
  );
}
