export default function PagePlaceholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold text-stone-900">{title}</h1>
      <p className="mt-2 text-sm text-stone-500">Coming in {phase}.</p>
    </div>
  );
}
