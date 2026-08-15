import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import CoverImage from "../components/CoverImage";
import { useAuth } from "../context/AuthContext";
import { useAddToCart } from "../hooks/useAddToCart";
import { useBook } from "../hooks/useBooks";
import { formatPrice } from "../lib/money";
import NotFoundPage from "./NotFoundPage";

export default function BookDetailPage() {
  const { id } = useParams();
  const bookId = /^\d+$/.test(id ?? "") ? Number(id) : NaN;
  const { data: book, isPending, isError, error } = useBook(bookId);
  const { status } = useAuth();
  const addToCart = useAddToCart();
  const [quantity, setQuantity] = useState(1);

  if (!Number.isInteger(bookId)) return <NotFoundPage />;
  if (isError && error instanceof ApiError && error.status === 404) return <NotFoundPage />;
  if (isError) return <div className="py-16 text-center text-sm text-red-700">{error.message}</div>;
  if (isPending) {
    return (
      <div className="flex gap-8">
        <div className="h-96 w-64 flex-none animate-pulse rounded-lg bg-stone-200" />
        <div className="flex-1 space-y-3 py-2">
          <div className="h-7 w-2/3 animate-pulse rounded bg-stone-200" />
          <div className="h-4 w-1/3 animate-pulse rounded bg-stone-200" />
          <div className="h-24 w-full animate-pulse rounded bg-stone-200" />
        </div>
      </div>
    );
  }

  const maxQuantity = Math.min(book.quantity, 99);
  const clamp = (n: number) => Math.min(Math.max(1, n), Math.max(1, maxQuantity));

  return (
    <div className="flex flex-col gap-8 md:flex-row">
      <CoverImage
        coverPath={book.cover_path}
        title={book.title}
        className="h-96 w-64 flex-none rounded-lg shadow-sm"
      />
      <div className="flex-1">
        <h1 className="text-3xl font-bold text-stone-900">{book.title}</h1>
        <p className="mt-1 text-stone-600">{book.authors.map((a) => a.name).join(", ")}</p>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {book.categories.map((c) => (
            <span
              key={c.category_id}
              className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800"
            >
              {c.name}
            </span>
          ))}
        </div>
        {book.publisher && <p className="mt-3 text-sm text-stone-500">Published by {book.publisher}</p>}
        {book.description && (
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-stone-700">{book.description}</p>
        )}

        <div className="mt-6 border-t border-stone-200 pt-5">
          <div className="flex items-center gap-4">
            <span className="text-2xl font-bold text-stone-900">{formatPrice(book.price_cents)}</span>
            {book.quantity === 0 ? (
              <span className="text-sm font-medium text-red-700">Out of stock</span>
            ) : book.quantity <= 5 ? (
              <span className="text-sm text-amber-700">Only {book.quantity} left</span>
            ) : (
              <span className="text-sm text-green-700">In stock</span>
            )}
          </div>

          {status === "anonymous" ? (
            <Link
              to="/login"
              className="mt-4 inline-block rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
            >
              Log in to add to cart
            </Link>
          ) : (
            <div className="mt-4 flex items-center gap-3">
              <input
                type="number"
                min={1}
                max={maxQuantity}
                value={quantity}
                onChange={(e) => setQuantity(clamp(parseInt(e.target.value, 10) || 1))}
                disabled={book.quantity === 0}
                className="w-20 rounded-md border border-stone-300 px-2.5 py-2 text-sm disabled:bg-stone-100"
              />
              <button
                onClick={() => addToCart.mutate({ bookId: book.book_id, quantity })}
                disabled={book.quantity === 0 || addToCart.isPending}
                className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
              >
                {addToCart.isPending ? "Adding…" : "Add to cart"}
              </button>
              {addToCart.isSuccess && <span className="text-sm text-green-700">Added ✓</span>}
              {addToCart.isError && (
                <span className="text-sm text-red-700">{addToCart.error.message}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
