import { Link } from "react-router-dom";
import type { CartLine } from "../api/types";
import CoverImage from "../components/CoverImage";
import { useCart, useRemoveCartItem, useUpdateCartItem } from "../hooks/useCart";
import { formatPrice } from "../lib/money";

function CartLineRow({ line }: { line: CartLine }) {
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const maxQuantity = Math.min(line.stock_remaining, 99);
  const stepClass =
    "h-7 w-7 rounded-md border border-stone-300 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-40 disabled:hover:bg-transparent";

  return (
    <div className="flex gap-4 border-b border-stone-200 py-4">
      <Link to={`/books/${line.book_id}`} className="flex-none">
        <CoverImage coverPath={line.cover_path} title={line.title} className="h-24 w-16 rounded" />
      </Link>
      <div className="min-w-0 flex-1">
        <Link
          to={`/books/${line.book_id}`}
          className="font-medium text-stone-900 hover:text-amber-700"
        >
          {line.title}
        </Link>
        <p className="mt-0.5 text-sm text-stone-500">{formatPrice(line.unit_price_cents)} each</p>
        {!line.is_available ? (
          <p className="mt-1 text-sm font-medium text-red-700">
            No longer available — not included in your total
          </p>
        ) : line.stock_remaining <= 5 ? (
          <p className="mt-1 text-sm text-amber-700">Only {line.stock_remaining} in stock</p>
        ) : null}
        {update.isError && (
          <p className="mt-1 text-sm text-red-700">{update.error.message}</p>
        )}
      </div>
      <div className="flex flex-none flex-col items-end justify-between">
        <button
          onClick={() => remove.mutate(line.cart_item_id)}
          disabled={remove.isPending}
          className="text-sm text-stone-400 hover:text-red-700 disabled:opacity-40"
          aria-label={`Remove ${line.title}`}
        >
          ✕ Remove
        </button>
        <div className="flex items-center gap-3">
          {line.is_available && (
            <div className="flex items-center gap-1.5">
              <button
                className={stepClass}
                disabled={line.quantity <= 1 || update.isPending}
                onClick={() =>
                  update.mutate({ cartItemId: line.cart_item_id, quantity: line.quantity - 1 })
                }
              >
                −
              </button>
              <span className="w-8 text-center text-sm text-stone-900">{line.quantity}</span>
              <button
                className={stepClass}
                disabled={line.quantity >= maxQuantity || update.isPending}
                onClick={() =>
                  update.mutate({ cartItemId: line.cart_item_id, quantity: line.quantity + 1 })
                }
              >
                +
              </button>
            </div>
          )}
          <span
            className={`w-20 text-right font-medium ${line.is_available ? "text-stone-900" : "text-stone-400 line-through"}`}
          >
            {formatPrice(line.line_total_cents)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function CartPage() {
  const { data: cart, isPending, isError, error } = useCart();

  if (isPending) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 3 }, (_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-lg bg-stone-200" />
        ))}
      </div>
    );
  }
  if (isError) return <div className="py-16 text-center text-sm text-red-700">{error.message}</div>;

  if (cart.items.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-lg font-medium text-stone-700">Your cart is empty.</p>
        <Link
          to="/"
          className="mt-4 inline-block rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
        >
          Browse the catalog
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <div className="flex-1">
        <h1 className="mb-2 text-2xl font-bold text-stone-900">Your cart</h1>
        {cart.items.map((line) => (
          <CartLineRow key={line.cart_item_id} line={line} />
        ))}
      </div>
      <div className="w-full flex-none lg:w-72">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-sm text-stone-600">
            <span>
              Subtotal ({cart.item_count} item{cart.item_count === 1 ? "" : "s"})
            </span>
            <span className="text-lg font-bold text-stone-900">
              {formatPrice(cart.subtotal_cents)}
            </span>
          </div>
          {cart.has_unavailable_lines ? (
            <>
              <p className="mt-3 text-sm text-amber-700">
                Remove the unavailable items to check out.
              </p>
              <span className="mt-3 block cursor-not-allowed rounded-md bg-stone-300 px-4 py-2 text-center text-sm font-medium text-white">
                Proceed to checkout
              </span>
            </>
          ) : (
            <Link
              to="/checkout"
              className="mt-4 block rounded-md bg-amber-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-amber-700"
            >
              Proceed to checkout
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
