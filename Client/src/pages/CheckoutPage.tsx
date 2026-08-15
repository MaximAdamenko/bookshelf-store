import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Field, FormError, SubmitButton } from "../components/form";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../hooks/useCart";
import { usePlaceOrder } from "../hooks/useOrders";
import { formatPrice } from "../lib/money";

export default function CheckoutPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: cart, isPending } = useCart();
  const place = usePlaceOrder();

  const [form, setForm] = useState({
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    street: "",
    city: "",
    apartment: "",
    postal_code: "",
    phone: "",
  });

  const set = (key: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  if (isPending) return <div className="h-64 animate-pulse rounded-lg bg-stone-200" />;

  if (!cart || cart.items.length === 0 || cart.has_unavailable_lines) {
    return (
      <div className="py-16 text-center">
        <p className="text-lg font-medium text-stone-700">
          {cart?.has_unavailable_lines
            ? "Some items in your cart are unavailable."
            : "Your cart is empty."}
        </p>
        <Link
          to={cart?.has_unavailable_lines ? "/cart" : "/"}
          className="mt-4 inline-block rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
        >
          {cart?.has_unavailable_lines ? "Back to cart" : "Browse the catalog"}
        </Link>
      </div>
    );
  }

  const lines = cart.items.filter((line) => line.is_available);

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    place.mutate(
      {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        street: form.street.trim(),
        city: form.city.trim(),
        postal_code: form.postal_code.trim(),
        ...(form.apartment.trim() ? { apartment: form.apartment.trim() } : {}),
        ...(form.phone.trim() ? { phone: form.phone.trim() } : {}),
      },
      {
        onSuccess: (order) =>
          navigate(`/orders/${order.order_id}`, { state: { placed: true }, replace: true }),
      },
    );
  };

  return (
    <div className="flex flex-col gap-8 lg:flex-row">
      <div className="flex-1">
        <h1 className="mb-4 text-2xl font-bold text-stone-900">Checkout</h1>
        <form onSubmit={onSubmit} className="max-w-md space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="First name"
              name="first_name"
              autoComplete="given-name"
              required
              maxLength={60}
              value={form.first_name}
              onChange={set("first_name")}
            />
            <Field
              label="Last name"
              name="last_name"
              autoComplete="family-name"
              required
              maxLength={60}
              value={form.last_name}
              onChange={set("last_name")}
            />
          </div>
          <Field
            label="Street address"
            name="street"
            autoComplete="street-address"
            required
            maxLength={200}
            value={form.street}
            onChange={set("street")}
          />
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="City"
              name="city"
              autoComplete="address-level2"
              required
              maxLength={100}
              value={form.city}
              onChange={set("city")}
            />
            <Field
              label="Apartment (optional)"
              name="apartment"
              maxLength={40}
              value={form.apartment}
              onChange={set("apartment")}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field
              label="Postal code"
              name="postal_code"
              autoComplete="postal-code"
              required
              maxLength={12}
              value={form.postal_code}
              onChange={set("postal_code")}
            />
            <Field
              label="Phone (optional)"
              name="phone"
              type="tel"
              autoComplete="tel"
              value={form.phone}
              onChange={set("phone")}
            />
          </div>
          <FormError message={place.error?.message ?? null} />
          <SubmitButton pending={place.isPending}>
            {place.isPending
              ? "Placing order…"
              : `Place order — ${formatPrice(cart.subtotal_cents)}`}
          </SubmitButton>
          <p className="text-xs text-stone-500">
            Payments are mocked in this project — no real charge happens.
          </p>
        </form>
      </div>
      <div className="w-full flex-none lg:w-80">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-semibold text-stone-900">Order summary</h2>
          <ul className="space-y-2">
            {lines.map((line) => (
              <li key={line.cart_item_id} className="flex justify-between gap-3 text-sm">
                <span className="min-w-0 truncate text-stone-700">
                  {line.title} <span className="text-stone-400">× {line.quantity}</span>
                </span>
                <span className="flex-none text-stone-900">
                  {formatPrice(line.line_total_cents)}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-4 flex items-center justify-between border-t border-stone-200 pt-3">
            <span className="text-sm text-stone-600">Total</span>
            <span className="text-lg font-bold text-stone-900">
              {formatPrice(cart.subtotal_cents)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
