export default function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center">
      <div
        className="animate-spin rounded-full border-2 border-indigo-500/20 border-t-indigo-500"
        style={{ width: size, height: size }}
      />
    </div>
  );
}
