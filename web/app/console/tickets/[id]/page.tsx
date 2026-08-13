import { notFound } from "next/navigation";

import { TicketDetail } from "@/components/console/ticket-detail";
import { getTicket, listRunEvents, listRuns } from "@/lib/api/server";

export default async function ConsoleTicketDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const ticketPromise = getTicket(id);
  const runsPromise = listRuns(id);
  let ticket;
  let runs;
  try {
    [ticket, runs] = await Promise.all([ticketPromise, runsPromise]);
  } catch {
    notFound();
  }
  const latest = runs.items[0] ?? null;
  const events = latest ? (await listRunEvents(latest.id)).items : [];

  return <TicketDetail ticket={ticket} run={latest} events={events} />;
}
