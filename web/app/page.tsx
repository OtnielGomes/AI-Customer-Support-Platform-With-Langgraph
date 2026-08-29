import Link from "next/link";
import { redirect } from "next/navigation";

import { portalLogoutAction } from "@/app/portal/actions";
import { HomeChat } from "@/components/portal/home-chat";
import { getPortalMe } from "@/lib/api/server";
import { getPortalEmail } from "@/lib/auth";

export default async function HomePage() {
  const email = await getPortalEmail();
  if (!email) {
    redirect("/portal/login");
  }
  const me = await getPortalMe();

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-12">
      <header className="mb-10 flex items-start justify-between gap-6">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">TechStore Support</p>
          <h1 className="mt-2 font-[family-name:var(--font-serif)] text-4xl">
            Olá, {me.name.split(" ")[0]}
          </h1>
          <p className="mt-3 max-w-xl text-[var(--muted)]">
            Você já está identificado como {me.email}. Seus pedidos estão abaixo — escolha um
            se quiser, ou descreva o que precisa.
          </p>
        </div>
        <div className="grid gap-2 text-right text-sm">
          <Link href="/login" className="text-[var(--muted)] hover:underline">
            Equipe
          </Link>
          <form action={portalLogoutAction}>
            <button type="submit" className="text-[var(--muted)] hover:underline">
              Sair
            </button>
          </form>
        </div>
      </header>
      <HomeChat orders={me.orders} />
      {me.conversations.length > 0 ? (
        <section className="mt-10 grid gap-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
            Conversas recentes
          </h2>
          {me.conversations.map((item) => (
            <Link
              key={item.id}
              href={`/tickets/${item.id}`}
              className="rounded-xl border border-[var(--line)] bg-[var(--card)] px-4 py-3 text-sm hover:border-[var(--accent)]"
            >
              {item.subject}
            </Link>
          ))}
        </section>
      ) : null}
    </main>
  );
}
