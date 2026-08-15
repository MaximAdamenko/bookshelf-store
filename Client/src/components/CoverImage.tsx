import { useState } from "react";
import { coverUrl } from "../api/books";

export default function CoverImage({
  coverPath,
  title,
  className,
}: {
  coverPath: string | null;
  title: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (!coverPath || failed) {
    return (
      <div className={`flex items-center justify-center bg-stone-200 text-4xl ${className ?? ""}`}>
        📖
      </div>
    );
  }
  return (
    <img
      src={coverUrl(coverPath)}
      alt={`Cover of ${title}`}
      onError={() => setFailed(true)}
      className={`object-cover ${className ?? ""}`}
    />
  );
}
