'use client';

import { Menu, Moon, Sun, Bell, Settings, User } from 'lucide-react';
import { useState } from 'react';

interface TopNavProps {
  onMenuClick: () => void;
  isDarkMode: boolean;
  onDarkModeToggle: () => void;
}

export default function TopNav({ onMenuClick, isDarkMode, onDarkModeToggle }: TopNavProps) {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="sticky top-0 z-30 bg-slate-900/80 backdrop-blur-lg border-b border-slate-800">
      <div className="flex items-center justify-between px-4 lg:px-6 h-16">
        {/* Left side */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="lg:hidden text-slate-400 hover:text-slate-100"
          >
            <Menu size={24} />
          </button>
          <div className="hidden lg:block">
            <h1 className="text-lg font-semibold text-slate-100">Dashboard</h1>
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2">
          {/* Dark mode toggle */}
          <button
            onClick={onDarkModeToggle}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDarkMode ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {/* Notifications */}
          <div className="relative">
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              <Bell size={20} />
            </button>
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-slate-800 border border-slate-700 rounded-lg shadow-xl p-4">
                <h3 className="text-sm font-semibold text-slate-200 mb-2">Notifications</h3>
                <p className="text-xs text-slate-400">No new notifications</p>
              </div>
            )}
          </div>

          {/* Settings */}
          <button className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors">
            <Settings size={20} />
          </button>

          {/* User */}
          <button className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors">
            <User size={20} />
          </button>
        </div>
      </div>
    </header>
  );
}
