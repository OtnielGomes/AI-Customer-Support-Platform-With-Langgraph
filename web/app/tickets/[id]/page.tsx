import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { TicketOrderPanel } from "@/components/order-summary-card";
import { ChatWindow } from "@/components/portal/chat-window";
import { getTicket, listTicketMessages } from "@/lib/api/server";
import { getPortalEmail } from "@/lib/auth";

export default async function TicketPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const email = await getPortalEmail();
  if (!email) {
    redirect("/portal/login");
  }
  const { id } = await params;
  let ticket;
  let messages;
  try {
    [ticket, messages] = await Promise.all([getTicket(id), listTicketMessages(id)]);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-12">
      <Link href="/" className="text-sm text-[var(--muted)] hover:underline">
        ← Início
      </Link>
      <div className="mt-8 grid gap-6">
        <TicketOrderPanel order={ticket.order} />
        <ChatWindow ticket={ticket} initialMessages={messages.items} />
      </div>
    </main>
  );
}
