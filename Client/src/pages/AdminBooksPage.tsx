import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { BookPublic } from "../api/types";
import CoverImage from "../components/CoverImage";
import Pagination from "../components/Pagination";
import { EmptyState, ErrorState, SkeletonList } from "../components/states";
import { useAdminBooks, useDeleteBook, useHardDeleteBook, usePatchBook } from "../hooks/useAdmin";
import { formatDate } from "../lib/dates";
import { formatPrice } from "../lib/money";

const PAGE_SIZE = 20;

export default function AdminBooksPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const pageRaw = parseInt(searchParams.get("page") ?? "1", 10);
  const page = Number.isInteger(pageRaw) && pageRaw >= 1 ? pageRaw : 1;
  const [searchText, setSearchText] = useState(q);

  const { data, isPending, isError, error } = useAdminBooks({
    q: q || undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const del = useDeleteBook();
  const hardDel = useHardDeleteBook();
  const patch = usePatchBook();
  const [rowError, setRowError] = useState<{ id: number; message: string } | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("page" in changes)) next.delete("page");
    setSearchParams(next);
  };

  const toggleActive = (book: BookPublic) => {
    setRowError(null);
    const onError = (err: Error) => setRowError({ id: book.book_id, message: err.message });
    if (book.is_active) del.mutate(book.book_id, { onError });
    else patch.mutate({ bookId: book.book_id, input: { is_active: true } }, { onError });
  };

  const remove = (book: BookPublic) => {
    setRowError(null);
    hardDel.mutate(book.book_id, {
      onSuccess: () => setConfirmId(null),
      onError: (err: Error) => setRowError({ id: book.book_id, message: err.message }),
    });
  };

  const rowBusy = (id: number) =>
    (del.isPending && del.variables === id) ||
    (hardDel.isPending && hardDel.variables === id) ||
    (patch.isPending && patch.variables?.bookId === id);

  const pageCount = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-stone-900">Manage books</h1>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: searchText.trim() || null });
          }}
          className="ml-auto flex items-center gap-2"
        >
          <input
            type="search"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search title, author…"
            className="w-56 rounded-md border border-stone-300 bg-white px-2.5 py-1.5 text-sm text-stone-900 focus:border-amber-500 focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100"
          >
            Search
          </button>
        </form>
        <Link
          to="/admin/books/new"
          className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
        >
          + New book
        </Link>
      </div>

      {isPending ? (
        <SkeletonList rows={5} />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : data.items.length === 0 ? (
        <EmptyState title={q ? "No books match." : "No books yet."} />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-stone-200 bg-white shadow-sm">
            {data.items.map((book) => (
              <div key={book.book_id} className="border-b border-stone-200 last:border-b-0">
                <div className="flex items-center gap-4 px-4 py-3">
                  <CoverImage
                    coverPath={book.cover_path}
                    title={book.title}
                    className="h-14 w-10 flex-none overflow-hidden rounded"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-stone-900">{book.title}</p>
                    <p className="truncate text-xs text-stone-500">
                      {book.authors.map((a) => a.name).join(", ")}
                    </p>
                  </div>
                  <span className="w-20 text-right text-sm text-stone-900">
                    {formatPrice(book.price_cents)}
                  </span>
                  <span
                    className={`w-16 text-right text-sm ${
                      book.quantity === 0 ? "font-medium text-red-700" : "text-stone-600"
                    }`}
                  >
                    {book.quantity} in stock
                  </span>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      book.is_active ? "bg-green-100 text-green-800" : "bg-stone-200 text-stone-600"
                    }`}
                  >
                    {book.is_active ? "active" : "inactive"}
                  </span>
                  <span className="hidden w-24 text-right text-xs text-stone-500 sm:block">
                    {formatDate(book.updated_at)}
                  </span>
                  <Link
                    to={`/admin/books/${book.book_id}/edit`}
                    className="text-sm font-medium text-amber-700 hover:text-amber-800"
                  >
                    Edit
                  </Link>
                  <button
                    onClick={() => toggleActive(book)}
                    disabled={rowBusy(book.book_id)}
                    className="w-24 rounded-md border border-stone-300 px-2.5 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-50"
                  >
                    {book.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    onClick={() => {
                      setRowError(null);
                      setConfirmId(confirmId === book.book_id ? null : book.book_id);
                    }}
                    disabled={rowBusy(book.book_id)}
                    className="rounded-md border border-red-300 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
                {confirmId === book.book_id && (
                  <div className="flex flex-wrap items-center gap-3 border-t border-red-200 bg-red-50 px-4 py-3">
                    <p className="flex-1 text-xs text-red-800">
                      Permanently delete <span className="font-medium">{book.title}</span>? It
                      disappears from every customer's cart and this cannot be undone. Past
                      orders keep their own snapshot and are unaffected.
                    </p>
                    <button
                      onClick={() => setConfirmId(null)}
                      className="rounded-md border border-stone-300 bg-white px-2.5 py-1 text-xs font-medium text-stone-700 hover:bg-stone-100"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => remove(book)}
                      disabled={rowBusy(book.book_id)}
                      className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      Delete permanently
                    </button>
                  </div>
                )}
                {rowError?.id === book.book_id && (
                  <p className="px-4 pb-2 text-xs text-red-700">{rowError.message}</p>
                )}
              </div>
            ))}
          </div>
          <Pagination page={page} pageCount={pageCount} onPage={(p) => update({ page: String(p) })} />
        </>
      )}
    </div>
  );
}
