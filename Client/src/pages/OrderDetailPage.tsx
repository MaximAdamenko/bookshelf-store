import { Link, useLocation, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { FormNotice } from "../components/form";
import OrderStatusChip from "../components/OrderStatusChip";
import { ErrorState, SkeletonBlock } from "../components/states";
import { useOrder } from "../hooks/useOrders";
import { formatDate } from "../lib/dates";
import { formatPrice } from "../lib/money";
import NotFoundPage from "./NotFoundPage";

export default function OrderDetailPage() {
  const { id } = useParams();
  const location = useLocation();
  const placed = (location.state as { placed?: boolean } | null)?.placed ?? false;
  const orderId = /^\d+$/.test(id ?? "") ? Number(id) : NaN;
  const { data: order, isPending, isError, error } = useOrder(orderId);

  if (!Number.isInteger(orderId)) return <NotFoundPage />;
  if (isError && error instanceof ApiError && error.status === 404) return <NotFoundPage />;
  if (isError) return <ErrorState message={error.message} />;
  if (isPending) return <SkeletonBlock />;

  const { shipping } = order;

  return (
    <div className="mx-auto max-w-2xl">
      {placed && (
        <div className="mb-6">
          <FormNotice>Order placed — thank you! A summary is below.</FormNotice>
        </div>
      )}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <Link to="/orders" className="text-sm text-amber-700 hover:text-amber-800">
            ← Your orders
          </Link>
          <h1 className="mt-1 text-2xl font-bold text-stone-900">Order #{order.order_id}</h1>
          <p className="mt-0.5 text-sm text-stone-500">{formatDate(order.order_date)}</p>
        </div>
        <OrderStatusChip status={order.status} />
      </div>

      <div className="rounded-lg border border-stone-200 bg-white shadow-sm">
        {order.items.map((item) => (
          <div
            key={item.order_item_id}
            className="flex items-center gap-4 border-b border-stone-200 px-4 py-3"
          >
            <div className="min-w-0 flex-1">
              {item.book_id ? (
                <Link
                  to={`/books/${item.book_id}`}
                  className="font-medium text-stone-900 hover:text-amber-700"
                >
                  {item.title}
                </Link>
              ) : (
                <span className="font-medium text-stone-900">{item.title}</span>
              )}
              <p className="text-sm text-stone-500">{item.authors}</p>
            </div>
            <span className="flex-none text-sm text-stone-600">
              {item.quantity} × {formatPrice(item.unit_price_cents)}
            </span>
            <span className="w-24 flex-none text-right font-medium text-stone-900">
              {formatPrice(item.total_price_cents)}
            </span>
          </div>
        ))}
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-sm text-stone-600">Total</span>
          <span className="text-lg font-bold text-stone-900">
            {formatPrice(order.amount_cents)}
          </span>
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="mb-2 font-semibold text-stone-900">Shipping to</h2>
        <p className="text-sm leading-relaxed text-stone-700">
          {shipping.first_name} {shipping.last_name}
          <br />
          {shipping.street}
          {shipping.apartment ? `, ${shipping.apartment}` : ""}
          <br />
          {shipping.city}, {shipping.postal_code}
          {shipping.phone ? (
            <>
              <br />
              {shipping.phone}
            </>
          ) : null}
        </p>
      </div>
    </div>
  );
}
