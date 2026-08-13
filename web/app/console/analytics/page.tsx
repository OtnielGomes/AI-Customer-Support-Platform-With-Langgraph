import { AnalyticsDashboard } from "@/components/console/analytics-dashboard";
import { getAnalyticsOverview, getToolAnalytics } from "@/lib/api/server";

export default async function AnalyticsPage() {
  const [overview, tools] = await Promise.all([
    getAnalyticsOverview(),
    getToolAnalytics(),
  ]);

  return (
    <div className="grid gap-6">
      <header>
        <h1 className="font-[family-name:var(--font-serif)] text-3xl text-white">Analytics</h1>
        <p className="mt-1 text-sm text-[#9aa3ad]">
          Cached for 30 seconds on the API. Refresh the page for a new snapshot.
        </p>
      </header>
      <AnalyticsDashboard overview={overview} tools={tools.items} />
    </div>
  );
}
