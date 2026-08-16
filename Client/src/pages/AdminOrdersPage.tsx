import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { AdminOrderTarget, OrderStatus } from "../api/types";
import OrderStatusChip from "../components/OrderStatusChip";
import Pagination from "../components/Pagination";
import { EmptyState, ErrorState, SkeletonList } from "../components/states";
import { useAdminOrders, useSetOrderStatus } from "../hooks/useAdmin";
import { formatDate } from "../lib/dates";
import { formatPrice } from "../lib/money";

const PAGE_SIZE = 20;
const STATUSES: OrderStatus[] = ["pending", "paid", "shipped", "cancelled"];

// mirror of the server's _ALLOWED_FROM map — display only, the server still decides
const TRANSITIONS: Record<OrderStatus, { to: AdminOrderTarget; label: string }[]> = {
  pending: [
    { to: "paid", label: "Mark paid" },
    { to: "cancelled", label: "Cancel" },
  ],
  paid: [
    { to: "shipped", label: "Mark shipped" },
    { to: "cancelled", label: "Cancel" },
  ],
  shipped: [],
  cancelled: [],
};

export default function AdminOrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const statusRaw = searchParams.get("status");
  const status = STATUSES.includes(statusRaw as OrderStatus)
    ? (statusRaw as OrderStatus)
    : undefined;
  const pageRaw = parseInt(searchParams.get("page") ?? "1", 10);
  const page = Number.isInteger(pageRaw) && pageRaw >= 1 ? pageRaw : 1;

  const { data, isPending, isError, error } = useAdminOrders({
    status,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const setStatus = useSetOrderStatus();
  const [confirmCancel, setConfirmCancel] = useState<number | null>(null);
  const [rowError, setRowError] = useState<{ id: number; message: string } | null>(null);

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page");
    setSearchParams(next);
  };

  const act = (orderId: number, to: AdminOrderTarget) => {
    if (to === "cancelled" && confirmCancel !== orderId) {
      setConfirmCancel(orderId);
      return;
    }
    setConfirmCancel(null);
    setRowError(null);
    setStatus.mutate(
      { orderId, status: to },
      { onError: (err) => setRowError({ id: orderId, message: err.message }) },
    );
  };

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-900">Manage orders</h1>
        <select
          value={status ?? ""}
          onChange={(e) => update({ status: e.target.value || null })}
          className="rounded-md border border-stone-300 bg-white px-2.5 py-1.5 text-sm text-stone-900 focus:border-amber-500 focus:outline-none"
        >
          <option value="">All statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {isPending ? (
        <SkeletonList rows={5} />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : data.items.length === 0 ? (
        <EmptyState title={status ? `No ${status} orders.` : "No orders yet."} />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
            {data.items.map((order) => {
              const busy = setStatus.isPending && setStatus.variables?.orderId === order.order_id;
              return (
                <div key={order.order_id} className="border-b border-stone-200 last:border-b-0">
                  <div className="flex items-center gap-4 px-4 py-3">
                    <span className="w-16 font-medium text-stone-900">#{order.order_id}</span>
                    <span className="w-28 text-sm text-stone-600">
                      {formatDate(order.order_date)}
                    </span>
                    <span className="min-w-0 flex-1 truncate text-sm text-stone-700">
                      {order.email}
                    </span>
                    <span className="w-14 text-right text-sm text-stone-600">
                      {order.item_count} item{order.item_count === 1 ? "" : "s"}
                    </span>
                    <span className="w-20 text-right font-medium text-stone-900">
                      {formatPrice(order.amount_cents)}
                    </span>
                    <OrderStatusChip status={order.status} />
                    <span className="flex w-52 justify-end gap-2">
                      {TRANSITIONS[order.status].map(({ to, label }) => {
                        const confirming = to === "cancelled" && confirmCancel === order.order_id;
                        return (
                          <button
                            key={to}
                            onClick={() => act(order.order_id, to)}
                            disabled={busy}
                            className={`rounded-md border px-2.5 py-1 text-xs font-medium disabled:opacity-50 ${
                              confirming
                                ? "border-red-300 bg-red-50 text-red-700 hover:bg-red-100"
                                : "border-stone-300 text-stone-700 hover:bg-stone-100"
                            }`}
                          >
                            {confirming ? "Confirm cancel" : label}
                          </button>
                        );
                      })}
                    </span>
                  </div>
                  {rowError?.id === order.order_id && (
                    <p className="px-4 pb-2 text-xs text-red-700">{rowError.message}</p>
                  )}
                </div>
              );
            })}
          </div>
          <Pagination page={page} pageCount={pageCount} onPage={(p) => update({ page: String(p) })} />
        </>
      )}
    </div>
  );
}
