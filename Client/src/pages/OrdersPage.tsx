import { Link, useSearchParams } from "react-router-dom";
import type { OrderStatus } from "../api/types";
import OrderStatusChip from "../components/OrderStatusChip";
import Pagination from "../components/Pagination";
import { EmptyState, ErrorState, SkeletonList } from "../components/states";
import { useOrders } from "../hooks/useOrders";
import { formatDate } from "../lib/dates";
import { formatPrice } from "../lib/money";

const PAGE_SIZE = 10;
const STATUSES: OrderStatus[] = ["pending", "paid", "shipped", "cancelled"];

export default function OrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const statusRaw = searchParams.get("status");
  const status = STATUSES.includes(statusRaw as OrderStatus)
    ? (statusRaw as OrderStatus)
    : undefined;
  const pageRaw = parseInt(searchParams.get("page") ?? "1", 10);
  const page = Number.isInteger(pageRaw) && pageRaw >= 1 ? pageRaw : 1;

  const { data, isPending, isError, error } = useOrders({
    status,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page");
    setSearchParams(next);
  };

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-stone-900">Your orders</h1>
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
        <SkeletonList rows={4} />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : data.items.length === 0 ? (
        <EmptyState
          title={status ? `No ${status} orders.` : "No orders yet."}
          action={
            <Link
              to="/"
              className="inline-block rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
            >
              Browse the catalog
            </Link>
          }
        />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
            {data.items.map((order) => (
              <Link
                key={order.order_id}
                to={`/orders/${order.order_id}`}
                className="flex items-center gap-4 border-b border-stone-200 px-4 py-3 last:border-b-0 hover:bg-stone-50"
              >
                <span className="w-20 font-medium text-stone-900">#{order.order_id}</span>
                <span className="w-28 text-sm text-stone-600">{formatDate(order.order_date)}</span>
                <OrderStatusChip status={order.status} />
                <span className="ml-auto text-sm text-stone-600">
                  {order.item_count} item{order.item_count === 1 ? "" : "s"}
                </span>
                <span className="w-24 text-right font-medium text-stone-900">
                  {formatPrice(order.amount_cents)}
                </span>
              </Link>
            ))}
          </div>
          <Pagination
            page={page}
            pageCount={pageCount}
            onPage={(p) => update({ page: String(p) })}
          />
        </>
      )}
    </div>
  );
}
