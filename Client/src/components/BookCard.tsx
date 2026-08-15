import { Link } from "react-router-dom";
import { formatPrice } from "../lib/money";
import type { BookPublic } from "../api/types";
import CoverImage from "./CoverImage";

export default function BookCard({ book }: { book: BookPublic }) {
  return (
    <Link
      to={`/books/${book.book_id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-stone-200 bg-white transition-shadow hover:shadow-md"
    >
      <CoverImage coverPath={book.cover_path} title={book.title} className="h-56 w-full" />
      <div className="flex flex-1 flex-col gap-1 p-3">
        <h2 className="line-clamp-2 text-sm font-semibold text-stone-900 group-hover:text-amber-700">
          {book.title}
        </h2>
        <p className="line-clamp-1 text-xs text-stone-500">
          {book.authors.map((a) => a.name).join(", ")}
        </p>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="text-sm font-bold text-stone-900">{formatPrice(book.price_cents)}</span>
          {book.quantity === 0 && (
            <span className="rounded bg-stone-100 px-1.5 py-0.5 text-xs text-stone-500">
              Out of stock
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
