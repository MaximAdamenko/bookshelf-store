import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold text-stone-900">Page not found</h1>
      <p className="mt-2 text-sm text-stone-500">Nothing lives at this address.</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-amber-700 hover:underline">
        Back to the catalog
      </Link>
    </div>
  );
}
