import Link from "next/link";
import { notFound } from "next/navigation";

import { TicketChat } from "@/components/portal/ticket-chat";
import { getTicket } from "@/lib/api/server";

export default async function TicketPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let ticket;
  try {
    ticket = await getTicket(id);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-12">
      <Link href="/" className="text-sm text-[var(--muted)] hover:underline">
        ← New ticket
      </Link>
      <div className="mt-8">
        <TicketChat ticket={ticket} />
      </div>
    </main>
  );
}
