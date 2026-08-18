import { redirect } from "next/navigation";

export default async function EscalationsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();
  query.set("status", "escalated");
  const extra = first(params.status);
  if (extra && extra !== "escalated") {
    query.set("status", extra);
  }
  redirect(`/console/inbox?${query.toString()}`);
}

function first(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}
