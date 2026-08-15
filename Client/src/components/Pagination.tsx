export default function Pagination({
  page,
  pageCount,
  onPage,
}: {
  page: number;
  pageCount: number;
  onPage: (page: number) => void;
}) {
  if (pageCount <= 1) return null;
  const buttonClass =
    "rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100 disabled:opacity-40 disabled:hover:bg-transparent";
  return (
    <div className="flex items-center justify-center gap-4 py-6">
      <button className={buttonClass} disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ← Previous
      </button>
      <span className="text-sm text-stone-600">
        Page {page} of {pageCount}
      </span>
      <button className={buttonClass} disabled={page >= pageCount} onClick={() => onPage(page + 1)}>
        Next →
      </button>
    </div>
  );
}
