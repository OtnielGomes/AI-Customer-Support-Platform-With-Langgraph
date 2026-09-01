import type { OrderSummary } from "@/lib/api/types";
import { formatDateOnly, formatMoney } from "@/lib/format";

export function OrderSummaryCard({
  order,
  variant = "portal",
}: {
  order: OrderSummary;
  variant?: "portal" | "console";
}) {
  const muted = variant === "console" ? "text-[#9aa3ad]" : "text-[var(--muted)]";
  const ink = variant === "console" ? "text-[#e8e4dc]" : "text-[var(--ink)]";
  const delivery = order.actual_delivery ?? order.estimated_delivery;
  const deliveryLabel = order.actual_delivery ? "Entregue em" : "Previsão de entrega";
  const paymentExtra =
    order.paid_payment_count >= 2 ? ` · ${order.paid_payment_count} pagamentos` : "";

  return (
    <dl className={`grid gap-2 text-sm ${ink}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>Pedido</dt>
        <dd>
          Pedido {order.display_number}
          <span className={`ml-2 font-mono text-xs ${muted}`}>{order.public_id}</span>
        </dd>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>Status</dt>
        <dd>{order.status_label}</dd>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>Pagamento</dt>
        <dd>
          {order.payment_status_label}
          {paymentExtra}
        </dd>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>{deliveryLabel}</dt>
        <dd>{formatDateOnly(delivery)}</dd>
      </div>
      <div>
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>Itens</dt>
        <dd className="mt-1">
          {order.items.length === 0 ? (
            <span className={muted}>Sem itens</span>
          ) : (
            <ul className="grid gap-1">
              {order.items.map((item) => (
                <li key={`${item.product_name}-${item.quantity}`}>
                  {item.quantity}× {item.product_name}
                </li>
              ))}
            </ul>
          )}
        </dd>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <dt className={`text-xs uppercase tracking-wide ${muted}`}>Total</dt>
        <dd>{formatMoney(order.total_amount, order.currency)}</dd>
      </div>
    </dl>
  );
}

export function TicketOrderPanel({
  order,
  variant = "portal",
}: {
  order: OrderSummary | null | undefined;
  variant?: "portal" | "console";
}) {
  const shell =
    variant === "console"
      ? "rounded-2xl border border-white/10 p-4 text-sm"
      : "rounded-2xl border border-[var(--line)] bg-[var(--card)] p-4 text-sm";
  const muted = variant === "console" ? "text-[#9aa3ad]" : "text-[var(--muted)]";

  if (!order) {
    return (
      <section className={shell}>
        <h2 className={`text-xs uppercase tracking-wide ${muted}`}>Pedido</h2>
        <p className={`mt-2 ${muted}`}>Nenhum pedido vinculado a este Ticket</p>
      </section>
    );
  }

  return (
    <section className={shell}>
      <OrderSummaryCard order={order} variant={variant} />
    </section>
  );
}
