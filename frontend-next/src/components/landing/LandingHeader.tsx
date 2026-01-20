'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Menu, X, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useStore } from '@/store';
import { useAuth } from '@/hooks';

const NAV_ITEMS = [
  { label: 'Why Arakis AI', href: '#why-arakis' },
  { label: 'Core Capabilities', href: '#capabilities' },
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'Pricing', href: '#pricing' },
  { label: 'Testimonials', href: '#testimonials' },
];

interface LandingHeaderProps {
  onStartTrial: () => void;
}

export function LandingHeader({ onStartTrial }: LandingHeaderProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const isAuthenticated = useStore((state) => state.auth.isAuthenticated);
  const user = useStore((state) => state.auth.user);
  const { logout } = useAuth();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-purple-800 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">A</span>
            </div>
            <span className="text-xl font-semibold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
              Arakis
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                {item.label}
              </a>
            ))}
          </nav>

          {/* CTA Buttons */}
          <div className="hidden md:flex items-center gap-4">
            {isAuthenticated || user ? (
              <>
                <span className="text-sm text-gray-600">
                  {user?.full_name || user?.email || 'User'}
                </span>
                <Button
                  onClick={onStartTrial}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-6"
                >
                  Go to App
                </Button>
                <Button
                  onClick={logout}
                  variant="outline"
                  className="text-gray-600 hover:text-gray-900"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </Button>
              </>
            ) : (
              <Button
                onClick={onStartTrial}
                className="bg-purple-600 hover:bg-purple-700 text-white px-6"
              >
                Start Free Trial
              </Button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 text-gray-600 hover:text-gray-900"
          >
            {isMobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-white border-t border-gray-100">
          <div className="px-4 py-4 space-y-3">
            {NAV_ITEMS.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className="block text-sm text-gray-600 hover:text-gray-900 py-2"
              >
                {item.label}
              </a>
            ))}
            {isAuthenticated || user ? (
              <>
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-sm text-gray-600 py-2">
                    {user?.full_name || user?.email || 'User'}
                  </p>
                </div>
                <Button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    onStartTrial();
                  }}
                  className="w-full bg-purple-600 hover:bg-purple-700 text-white"
                >
                  Go to App
                </Button>
                <Button
                  onClick={() => {
                    setIsMobileMenuOpen(false);
                    logout();
                  }}
                  variant="outline"
                  className="w-full text-gray-600 hover:text-gray-900"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Log out
                </Button>
              </>
            ) : (
              <Button
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  onStartTrial();
                }}
                className="w-full bg-purple-600 hover:bg-purple-700 text-white mt-4"
              >
                Start Free Trial
              </Button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
