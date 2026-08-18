"use client";

import { useState } from "react";

import { NewConversation } from "@/components/portal/chat-window";
import { OrderPicker } from "@/components/portal/order-picker";
import type { OrderSummary } from "@/lib/api/types";

export function HomeChat({ orders }: { orders: OrderSummary[] }) {
  const [orderId, setOrderId] = useState<string | null>(
    orders.length === 1 ? orders[0].id : null,
  );

  return (
    <div className="grid gap-6">
      <section className="grid gap-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-[var(--muted)]">
          Seus pedidos
        </h2>
        <OrderPicker orders={orders} selectedId={orderId} onSelect={setOrderId} />
      </section>
      <section className="rounded-3xl border border-[var(--line)] bg-[var(--card)] p-6">
        <NewConversation orderId={orderId} />
      </section>
    </div>
  );
}
