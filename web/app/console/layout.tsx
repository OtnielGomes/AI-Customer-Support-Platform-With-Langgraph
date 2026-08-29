import Link from "next/link";

import { logoutAction } from "@/app/console/actions";
import { SwrProvider } from "@/components/console/swr-provider";

const LINKS = [
  { href: "/console/inbox", label: "Inbox" },
  { href: "/console/tickets", label: "Tickets" },
  { href: "/console/analytics", label: "Analytics" },
];

export default function ConsoleLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#12151a] text-[#e8e4dc]">
      <div className="grid min-h-screen lg:grid-cols-[240px_1fr]">
        <aside className="border-b border-white/10 px-5 py-6 lg:border-r lg:border-b-0">
          <p className="text-xs uppercase tracking-[0.25em] text-[#9aa3ad]">
            TechStore Support
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-serif)] text-2xl">
            Console
          </h1>
          <nav className="mt-8 grid gap-2 text-sm">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-[#c5cdd6] hover:bg-white/5 hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <form action={logoutAction} className="mt-10">
            <button type="submit" className="text-xs text-[#9aa3ad] hover:text-white">
              Sign out
            </button>
          </form>
        </aside>
        <div className="min-w-0 bg-[#181c22] p-6 lg:p-10">
          <SwrProvider>{children}</SwrProvider>
        </div>
      </div>
    </div>
  );
}
