import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorAlert({ message, onRetry }: ErrorAlertProps) {
  return (
    <div className="bg-red-900/20 border border-red-800 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="text-red-400 flex-shrink-0 mt-0.5" size={20} />
        <div className="flex-1">
          <p className="text-red-400 font-medium mb-1">Error</p>
          <p className="text-red-300 text-sm">{message}</p>
        </div>
        {onRetry && (
          <button
            onClick={onRetry}
            className="flex-shrink-0 p-2 text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded-lg transition-colors"
            title="Retry"
          >
            <RefreshCw size={16} />
          </button>
        )}
      </div>
    </div>
  );
}
