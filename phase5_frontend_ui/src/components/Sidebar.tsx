'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Database, Layers, AlertTriangle, Lightbulb, Users, FileText, Search, Activity, Sparkles, X } from 'lucide-react';
import { useState, useEffect } from 'react';

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

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const [mounted, setMounted] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-64 bg-slate-900 border-r border-slate-800
          transform transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between p-6 border-b border-slate-800">
            <Link href="/" className="flex items-center gap-2">
              <Sparkles className="text-indigo-500" size={24} />
              <span className="text-lg font-bold bg-gradient-to-r from-slate-50 to-indigo-500 bg-clip-text text-transparent">
                Review Engine
              </span>
            </Link>
            <button
              onClick={onClose}
              className="lg:hidden text-slate-400 hover:text-slate-100"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto p-4">
            <ul className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      onClick={() => onClose()}
                      className={`
                        flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors
                        ${isActive
                          ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800'
                        }
                      `}
                    >
                      <Icon size={18} />
                      <span>{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-slate-800">
            <div className="text-xs text-slate-500">
              <p>AI-Powered Review</p>
              <p>Discovery Engine v1.0</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
