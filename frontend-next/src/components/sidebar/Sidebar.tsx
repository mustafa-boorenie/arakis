'use client';

import { useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/store';
import { useAuth } from '@/hooks';
import {
  PlusCircle,
  PenTool,
  FolderOpen,
  BarChart3,
  Users,
  Puzzle,
  FileText,
  Settings,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react';

type NavItem = {
  id: string;
  label: string;
  icon: React.ElementType;
  href?: string;
  action?: () => void;
};

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { logout } = useAuth();
  const { resetChat, setLayoutMode, setViewMode, setCurrentView } = useStore();
  const currentView = useStore((state) => state.layout.currentView);
  const [isDarkMode, setIsDarkMode] = useState(false);

  const handleNewReview = () => {
    resetChat();
    setLayoutMode('chat-fullscreen');
    setViewMode('new-review');
    setCurrentView('dashboard');
    // Navigate to home if not already there
    if (window.location.pathname !== '/') {
      router.push('/');
    }
  };

  const handleNavClick = (item: NavItem) => {
    if (item.action) {
      item.action();
    } else if (item.href) {
      router.push(item.href);
    }
  };

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'New Review', icon: PlusCircle, action: handleNewReview },
    { id: 'ai-writer', label: 'AI Writer', icon: PenTool, action: () => setCurrentView('ai-writer') },
    { id: 'project', label: 'Project', icon: FolderOpen, action: () => setCurrentView('project') },
    { id: 'analytics', label: 'Analytics', icon: BarChart3, action: () => setCurrentView('analytics') },
    { id: 'teams', label: 'Teams', icon: Users, action: () => setCurrentView('teams') },
    { id: 'integrations', label: 'Integrations', icon: Puzzle, action: () => setCurrentView('integrations') },
    { id: 'docs', label: 'Documentations', icon: FileText, action: () => setCurrentView('docs') },
    { id: 'settings', label: 'Settings', icon: Settings, href: '/settings' },
  ];

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
    // TODO: Implement actual dark mode toggle
  };

  return (
    <div className="h-full w-[72px] flex flex-col bg-gradient-to-b from-purple-700 to-purple-900 text-white">
      {/* Logo */}
      <div className="flex items-center justify-center py-5">
        <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center backdrop-blur">
          <span className="text-white font-bold text-lg">A</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col items-center py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id || (item.id === 'settings' && pathname === '/settings');
          return (
            <button
              key={item.id}
              onClick={() => handleNavClick(item)}
              className={`
                group relative w-12 h-12 flex items-center justify-center rounded-xl
                transition-all duration-200
                ${isActive
                  ? 'bg-white/20 text-white'
                  : 'text-white/60 hover:text-white hover:bg-white/10'
                }
              `}
              title={item.label}
            >
              <Icon className="w-5 h-5" />

              {/* Tooltip */}
              <div className="
                absolute left-full ml-3 px-3 py-1.5
                bg-gray-900 text-white text-sm rounded-lg
                opacity-0 group-hover:opacity-100
                pointer-events-none transition-opacity
                whitespace-nowrap z-50
              ">
                {item.label}
              </div>

              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 w-1 h-6 bg-white rounded-r-full" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="flex flex-col items-center py-4 space-y-2 border-t border-white/10">
        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          className="w-12 h-12 flex items-center justify-center rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all"
          title={isDarkMode ? 'Light Mode' : 'Dark Mode'}
        >
          <div className="relative w-10 h-5 bg-white/20 rounded-full p-0.5">
            <div className={`
              w-4 h-4 rounded-full bg-white flex items-center justify-center
              transition-transform duration-200
              ${isDarkMode ? 'translate-x-5' : 'translate-x-0'}
            `}>
              {isDarkMode ? (
                <Moon className="w-2.5 h-2.5 text-purple-700" />
              ) : (
                <Sun className="w-2.5 h-2.5 text-purple-700" />
              )}
            </div>
          </div>
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="group relative w-12 h-12 flex items-center justify-center rounded-xl text-white/60 hover:text-white hover:bg-white/10 transition-all"
          title="Log out"
        >
          <LogOut className="w-5 h-5" />

          {/* Tooltip */}
          <div className="
            absolute left-full ml-3 px-3 py-1.5
            bg-gray-900 text-white text-sm rounded-lg
            opacity-0 group-hover:opacity-100
            pointer-events-none transition-opacity
            whitespace-nowrap z-50
          ">
            Log out
          </div>
        </button>
      </div>
    </div>
  );
}
