import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: LucideIcon;
  iconColor?: string;
}

export default function MetricCard({ title, value, change, icon: Icon, iconColor = 'text-indigo-500' }: MetricCardProps) {
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <span className="text-slate-400 text-sm font-medium">{title}</span>
        <Icon className={iconColor} size={20} />
      </div>
      <div className="text-3xl font-bold mb-2">{value}</div>
      {change && (
        <div className="text-sm text-emerald-400">{change}</div>
      )}
    </div>
  );
}
