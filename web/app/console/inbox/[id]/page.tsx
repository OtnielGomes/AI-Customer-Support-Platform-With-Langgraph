import { notFound } from "next/navigation";

import { InboxThread } from "@/components/console/inbox-thread";
import { getTicket, listRuns, listRunEvents, listTicketMessages } from "@/lib/api/server";

export default async function InboxThreadPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  try {
    const [ticket, messages, runs] = await Promise.all([
      getTicket(id),
      listTicketMessages(id),
      listRuns(id),
    ]);
    const run = runs.items[0] ?? null;
    const events = run ? (await listRunEvents(run.id)).items : [];
    return (
      <InboxThread ticket={ticket} messages={messages.items} run={run} events={events} />
    );
  } catch {
    notFound();
  }
}
