'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sparkles, Database, Layers, AlertTriangle, Lightbulb, Users, FileText, Search, Activity } from 'lucide-react';

const navItems = [
  { href: '/', label: 'Overview', icon: Database },
  { href: '/themes', label: 'Themes', icon: Layers },
  { href: '/pain-points', label: 'Pain Points', icon: AlertTriangle },
  { href: '/feature-requests', label: 'Feature Requests', icon: Lightbulb },
  { href: '/segments', label: 'User Segments', icon: Users },
  { href: '/executive-summary', label: 'Executive Summary', icon: FileText },
  { href: '/search', label: 'Search Reviews', icon: Search },
  { href: '/pipeline', label: 'Pipeline Status', icon: Activity },
];

export default function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="bg-slate-900 border-b border-slate-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="text-indigo-500" size={24} />
            <span className="text-xl font-bold bg-gradient-to-r from-slate-50 to-indigo-500 bg-clip-text text-transparent">
              Review Discovery Engine
            </span>
          </Link>
          
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-500/10 text-indigo-400'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                  }`}
                >
                  <Icon size={16} />
                  <span className="hidden md:inline">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
