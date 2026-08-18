import { InboxList } from "@/components/console/inbox-list";

export default async function InboxPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const params = await searchParams;
  return (
    <div className="grid gap-6">
      <header>
        <h1 className="font-[family-name:var(--font-serif)] text-3xl text-white">Inbox</h1>
        <p className="mt-1 text-sm text-[#9aa3ad]">
          Conversas ao vivo, mais recentes primeiro.
        </p>
      </header>
      <InboxList status={params.status} />
    </div>
  );
}
