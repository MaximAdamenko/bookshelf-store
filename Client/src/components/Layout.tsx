import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useCart } from "../hooks/useCart";

function CartBadge() {
  const { data } = useCart();
  const count = data?.item_count ?? 0;
  if (count === 0) return null;
  return (
    <span className="absolute -top-2 -right-3 flex h-5 min-w-5 items-center justify-center rounded-full bg-amber-600 px-1 text-xs font-semibold text-white">
      {count > 99 ? "99+" : count}
    </span>
  );
}

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium transition-colors ${
    isActive ? "text-amber-700" : "text-stone-600 hover:text-stone-900"
  }`;

export default function Layout() {
  const { user, status, isAdmin, logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-stone-50 text-stone-900">
      <header className="sticky top-0 z-10 border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-8">
            <Link to="/" className="text-lg font-bold tracking-tight text-stone-900">
              📚 Book Shelf
            </Link>
            <nav className="flex items-center gap-6">
              <NavLink to="/" end className={navLinkClass}>
                Catalog
              </NavLink>
              {status === "authenticated" && (
                <>
                  <NavLink to="/cart" className={navLinkClass}>
                    <span className="relative">
                      Cart
                      <CartBadge />
                    </span>
                  </NavLink>
                  <NavLink to="/orders" end className={navLinkClass}>
                    Orders
                  </NavLink>
                </>
              )}
              {isAdmin && (
                <>
                  <NavLink to="/admin/books" className={navLinkClass}>
                    Manage books
                  </NavLink>
                  <NavLink to="/admin/orders" className={navLinkClass}>
                    Manage orders
                  </NavLink>
                </>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            {status === "authenticated" && user ? (
              <>
                <span className="text-sm text-stone-600">Hi, {user.first_name}</span>
                <button
                  onClick={logout}
                  className="rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100"
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-stone-600 hover:text-stone-900">
                  Log in
                </Link>
                <Link
                  to="/register"
                  className="rounded-md bg-amber-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-700"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>

      <footer className="border-t border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4 text-center text-xs text-stone-500">
          Book Shelf — a security-first bookstore project
        </div>
      </footer>
    </div>
  );
}
