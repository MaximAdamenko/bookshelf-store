import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import BookCard from "../components/BookCard";
import Pagination from "../components/Pagination";
import { EmptyState, ErrorState, SkeletonGrid } from "../components/states";
import { useBooks, useCategories } from "../hooks/useBooks";
import type { BookSort } from "../api/types";

const PAGE_SIZE = 12;
const SORTS: { value: BookSort; label: string }[] = [
  { value: "newest", label: "Newest" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "relevance", label: "Relevance" },
];

function toInt(raw: string | null): number | undefined {
  if (!raw) return undefined;
  const n = parseInt(raw, 10);
  return Number.isInteger(n) && n >= 0 ? n : undefined;
}

export default function HomePage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = searchParams.get("q") ?? "";
  const categoryId = toInt(searchParams.get("category"));
  const minDollars = toInt(searchParams.get("min"));
  const maxDollars = toInt(searchParams.get("max"));
  const inStock = searchParams.get("stock") === "1";
  const sortRaw = searchParams.get("sort");
  const sort = SORTS.some((s) => s.value === sortRaw) ? (sortRaw as BookSort) : "newest";
  const page = Math.max(1, toInt(searchParams.get("page")) ?? 1);

  const [searchText, setSearchText] = useState(q);
  const { data: categories } = useCategories();
  const { data, isPending, isError, error } = useBooks({
    q: q || undefined,
    category_id: categoryId,
    min_price_cents: minDollars !== undefined ? minDollars * 100 : undefined,
    max_price_cents: maxDollars !== undefined ? maxDollars * 100 : undefined,
    in_stock: inStock || undefined,
    sort,
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

  const fieldClass =
    "rounded-md border border-stone-300 bg-white px-2.5 py-1.5 text-sm text-stone-900 focus:border-amber-500 focus:outline-none";

  return (
    <div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          update({ q: searchText.trim() || null });
        }}
        className="mb-6 flex flex-wrap items-center gap-3"
      >
        <input
          type="search"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search title, author, description…"
          className={`${fieldClass} w-64 flex-none`}
        />
        <button
          type="submit"
          className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
        >
          Search
        </button>
        <select
          value={categoryId ?? ""}
          onChange={(e) => update({ category: e.target.value || null })}
          className={fieldClass}
        >
          <option value="">All genres</option>
          {categories?.map((c) => (
            <option key={c.category_id} value={c.category_id}>
              {c.name}
            </option>
          ))}
        </select>
        <div className="flex items-center gap-1.5 text-sm text-stone-600">
          <span>$</span>
          <input
            type="number"
            min={0}
            value={minDollars ?? ""}
            onChange={(e) => update({ min: e.target.value })}
            placeholder="Min"
            className={`${fieldClass} w-20`}
          />
          <span>–</span>
          <input
            type="number"
            min={0}
            value={maxDollars ?? ""}
            onChange={(e) => update({ max: e.target.value })}
            placeholder="Max"
            className={`${fieldClass} w-20`}
          />
        </div>
        <label className="flex items-center gap-1.5 text-sm text-stone-600">
          <input
            type="checkbox"
            checked={inStock}
            onChange={(e) => update({ stock: e.target.checked ? "1" : null })}
            className="accent-amber-600"
          />
          In stock only
        </label>
        <select
          value={sort}
          onChange={(e) => update({ sort: e.target.value === "newest" ? null : e.target.value })}
          className={`${fieldClass} ml-auto`}
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </form>

      {isPending ? (
        <SkeletonGrid cards={8} />
      ) : isError ? (
        <ErrorState message={error.message} />
      ) : data.items.length === 0 ? (
        <EmptyState title="No books match." hint="Try clearing a filter or two." />
      ) : (
        <>
          <p className="mb-3 text-xs text-stone-500">
            {data.total} book{data.total === 1 ? "" : "s"}
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            {data.items.map((book) => (
              <BookCard key={book.book_id} book={book} />
            ))}
          </div>
          <Pagination page={page} pageCount={pageCount} onPage={(p) => update({ page: String(p) })} />
        </>
      )}
    </div>
  );
}
