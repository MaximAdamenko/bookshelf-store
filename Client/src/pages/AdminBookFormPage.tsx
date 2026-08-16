import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import type { BookCreateInput, BookPublic } from "../api/types";
import CoverImage from "../components/CoverImage";
import { Field, FormError, TextAreaField } from "../components/form";
import { useAdminBook, useCreateBook, usePatchBook, useUploadCover } from "../hooks/useAdmin";
import { useAuthors, useCategories, usePublishers } from "../hooks/useBooks";
import NotFoundPage from "./NotFoundPage";

export default function AdminBookFormPage() {
  const { id } = useParams();
  if (id === undefined) return <BookForm />;
  return <EditLoader bookId={parseInt(id, 10)} />;
}

function EditLoader({ bookId }: { bookId: number }) {
  const { data, isPending, isError, error } = useAdminBook(bookId);
  if (!Number.isInteger(bookId) || bookId < 1) return <NotFoundPage />;
  if (isError && error instanceof ApiError && error.status === 404) return <NotFoundPage />;
  if (isError) return <div className="py-16 text-center text-sm text-red-700">{error.message}</div>;
  if (isPending)
    return <div className="mx-auto h-96 max-w-2xl animate-pulse rounded-lg bg-stone-200" />;
  return <BookForm book={data} />;
}

function RefPicker({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { id: number; name: string }[];
  selected: number[];
  onToggle: (id: number) => void;
}) {
  return (
    <div>
      <span className="block text-sm font-medium text-stone-700">{label}</span>
      <div className="mt-1 flex flex-wrap gap-1.5 rounded-md border border-stone-300 bg-white p-2">
        {options.map((option) => {
          const active = selected.includes(option.id);
          return (
            <button
              key={option.id}
              type="button"
              aria-pressed={active}
              onClick={() => onToggle(option.id)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                active ? "bg-amber-600 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200"
              }`}
            >
              {option.name}
            </button>
          );
        })}
      </div>
      <p className="mt-1 text-xs text-stone-500">Pick 1–10.</p>
    </div>
  );
}

const dollars = (cents: number) => (cents / 100).toFixed(2);

function BookForm({ book }: { book?: BookPublic }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { data: authors } = useAuthors();
  const { data: categories } = useCategories();
  const { data: publishers } = usePublishers();
  const create = useCreateBook();
  const patch = usePatchBook();
  const upload = useUploadCover();

  const [form, setForm] = useState({
    title: book?.title ?? "",
    description: book?.description ?? "",
    price: book ? dollars(book.price_cents) : "",
    quantity: book ? String(book.quantity) : "0",
    publisher_id: book?.publisher_id ? String(book.publisher_id) : "",
  });
  const [authorIds, setAuthorIds] = useState<number[]>(book?.authors.map((a) => a.author_id) ?? []);
  const [categoryIds, setCategoryIds] = useState<number[]>(
    book?.categories.map((c) => c.category_id) ?? [],
  );
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [formError, setFormError] = useState<string | null>(
    (location.state as { coverError?: string } | null)?.coverError ?? null,
  );

  const set =
    (key: keyof typeof form) =>
    (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const toggle = (list: number[], setList: (v: number[]) => void) => (id: number) =>
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  const coverPreview = useMemo(
    () => (coverFile ? URL.createObjectURL(coverFile) : null),
    [coverFile],
  );
  useEffect(
    () => () => {
      if (coverPreview) URL.revokeObjectURL(coverPreview);
    },
    [coverPreview],
  );

  const pending = create.isPending || patch.isPending || upload.isPending;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const priceCents = Math.round(parseFloat(form.price) * 100);
    const quantity = parseInt(form.quantity, 10);
    if (!/^\d+(\.\d{1,2})?$/.test(form.price.trim()) || priceCents < 0) {
      setFormError("Price must be a dollar amount like 24.99.");
      return;
    }
    if (!Number.isInteger(quantity) || quantity < 0) {
      setFormError("Quantity must be a whole number, 0 or more.");
      return;
    }
    if (authorIds.length === 0 || categoryIds.length === 0) {
      setFormError("Pick at least one author and one category.");
      return;
    }

    // is_active is deliberately absent: the table's Activate/Deactivate owns it
    const payload: BookCreateInput = {
      title: form.title.trim(),
      description: form.description.trim(),
      price_cents: priceCents,
      quantity,
      author_ids: authorIds,
      category_ids: categoryIds,
      publisher_id: form.publisher_id ? parseInt(form.publisher_id, 10) : null,
    };

    let saved: BookPublic;
    try {
      saved = book
        ? await patch.mutateAsync({ bookId: book.book_id, input: payload })
        : await create.mutateAsync(payload);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Save failed");
      return;
    }

    if (coverFile) {
      try {
        await upload.mutateAsync({ bookId: saved.book_id, file: coverFile });
      } catch (err) {
        const message = `Book saved, but the cover was rejected: ${
          err instanceof Error ? err.message : "upload failed"
        }`;
        // a fresh create now exists — land on its edit page so resubmitting
        // can't create a duplicate
        if (book) setFormError(message);
        else
          navigate(`/admin/books/${saved.book_id}/edit`, {
            replace: true,
            state: { coverError: message },
          });
        return;
      }
    }
    navigate("/admin/books");
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold text-stone-900">
        {book ? `Edit book #${book.book_id}` : "New book"}
      </h1>
      <form
        onSubmit={onSubmit}
        className="mt-6 space-y-4 rounded-lg border border-stone-200 bg-white p-6 shadow-sm"
      >
        <Field
          label="Title"
          name="title"
          required
          maxLength={300}
          value={form.title}
          onChange={set("title")}
        />
        <TextAreaField
          label="Description"
          name="description"
          rows={5}
          maxLength={5000}
          value={form.description}
          onChange={set("description")}
        />
        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Price (USD)"
            name="price"
            required
            inputMode="decimal"
            placeholder="24.99"
            value={form.price}
            onChange={set("price")}
          />
          <Field
            label="Quantity in stock"
            name="quantity"
            required
            inputMode="numeric"
            value={form.quantity}
            onChange={set("quantity")}
          />
        </div>
        <div>
          <label htmlFor="publisher_id" className="block text-sm font-medium text-stone-700">
            Publisher
          </label>
          <select
            id="publisher_id"
            value={form.publisher_id}
            onChange={set("publisher_id")}
            className="mt-1 w-full rounded-md border border-stone-300 bg-white px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
          >
            <option value="">— No publisher —</option>
            {(publishers ?? []).map((p) => (
              <option key={p.publisher_id} value={p.publisher_id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <RefPicker
          label="Authors"
          options={(authors ?? []).map((a) => ({ id: a.author_id, name: a.name }))}
          selected={authorIds}
          onToggle={toggle(authorIds, setAuthorIds)}
        />
        <RefPicker
          label="Categories"
          options={(categories ?? []).map((c) => ({ id: c.category_id, name: c.name }))}
          selected={categoryIds}
          onToggle={toggle(categoryIds, setCategoryIds)}
        />
        <div>
          <span className="block text-sm font-medium text-stone-700">Cover</span>
          <div className="mt-1 flex items-start gap-4">
            {coverPreview ? (
              <img
                src={coverPreview}
                alt="New cover preview"
                className="h-40 w-28 flex-none rounded object-cover"
              />
            ) : (
              <CoverImage
                coverPath={book?.cover_path ?? null}
                title={form.title || "cover"}
                className="h-40 w-28 flex-none overflow-hidden rounded"
              />
            )}
            <div className="flex-1">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm text-stone-600 file:mr-3 file:rounded-md file:border-0 file:bg-stone-200 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-stone-700 hover:file:bg-stone-300"
              />
              <p className="mt-1 text-xs text-stone-500">
                JPEG, PNG or WebP. Uploaded when you save.
              </p>
            </div>
          </div>
        </div>
        <FormError message={formError} />
        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={pending}
            className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {pending ? "Saving…" : book ? "Save changes" : "Create book"}
          </button>
          <Link to="/admin/books" className="text-sm font-medium text-stone-600 hover:text-stone-900">
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
