export default function SkeletonCard() {
  return (
    <div className="card animate-pulse">
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 bg-slate-700 rounded w-1/3"></div>
        <div className="h-5 w-5 bg-slate-700 rounded"></div>
      </div>
      <div className="h-8 bg-slate-700 rounded w-1/2 mb-2"></div>
      <div className="h-3 bg-slate-700 rounded w-1/4"></div>
    </div>
  );
}
