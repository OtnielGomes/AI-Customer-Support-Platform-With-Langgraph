"use client";

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
    <div className="flex flex-wrap gap-2">
      {orders.map((order) => {
        const active = selectedId === order.id;
        return (
          <button
            key={order.id}
            type="button"
            onClick={() => onSelect(active ? null : order.id)}
            className={`rounded-full border px-3 py-1.5 text-xs ${
              active
                ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--accent-ink)]"
                : "border-[var(--line)] bg-white text-[var(--ink)]"
            }`}
          >
            {order.public_id} · {order.status} · {order.currency} {order.total_amount}
          </button>
        );
      })}
    </div>
  );
}
