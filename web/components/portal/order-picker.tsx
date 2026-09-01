"use client";

import { OrderSummaryCard } from "@/components/order-summary-card";
import { formatMoney } from "@/lib/format";
import type { OrderSummary } from "@/lib/api/types";

export function OrderPicker({
  orders,
  selectedId,
  onSelect,
}: {
  orders: OrderSummary[];
  selectedId: string | null;
  onSelect: (orderId: string | null) => void;
}) {
  if (orders.length === 0) {
    return <p className="text-sm text-[var(--muted)]">Nenhum pedido encontrado nesta conta.</p>;
  }

  return (
    <div className="grid gap-3">
      {orders.map((order) => {
        const active = selectedId === order.id;
        return (
          <div key={order.id} className="grid gap-2">
            <button
              type="button"
              onClick={() => onSelect(active ? null : order.id)}
              className={`flex w-full items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-left text-sm ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-ink)]"
                  : "border-[var(--line)] bg-white text-[var(--ink)]"
              }`}
            >
              <span>Pedido {order.display_number}</span>
              <span className={active ? "opacity-90" : "text-[var(--muted)]"}>
                {order.status_label} · {formatMoney(order.total_amount, order.currency)}
              </span>
            </button>
            {active ? (
              <div className="rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4">
                <OrderSummaryCard order={order} />
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
