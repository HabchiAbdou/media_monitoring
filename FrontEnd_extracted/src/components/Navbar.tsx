import React, { useState } from 'react';
import { Button } from './Button';
import { Menu, X, Radio } from 'lucide-react';

interface NavbarProps {
  isLoggedIn: boolean;
  username?: string;
  currentView?: string;
  onLogin?: () => void;
  onLogout?: () => void;
  onNavigate?: (view: string) => void;
}

export function Navbar({ isLoggedIn, username = 'User', currentView = 'dashboard', onLogin, onLogout, onNavigate }: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(word => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <nav className="bg-[var(--color-text-main)] text-white h-16 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full">
        <div className="flex items-center justify-between h-full">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <Radio className="w-6 h-6" />
            <span className="font-semibold text-lg">Media Monitor</span>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            <button 
              onClick={() => onNavigate?.('dashboard')} 
              className={`hover:text-gray-300 transition-colors ${currentView === 'dashboard' ? 'text-white border-b-2 border-white pb-1' : ''}`}
            >
              Dashboard
            </button>
            <button 
              onClick={() => onNavigate?.('reports')} 
              className={`hover:text-gray-300 transition-colors ${currentView === 'reports' ? 'text-white border-b-2 border-white pb-1' : ''}`}
            >
              Reports
            </button>
            <button 
              onClick={() => onNavigate?.('admin')} 
              className={`hover:text-gray-300 transition-colors ${currentView === 'admin' ? 'text-white border-b-2 border-white pb-1' : ''}`}
            >
              Admin
            </button>
          </div>

          {/* Desktop Auth */}
          <div className="hidden md:flex items-center gap-4">
            {isLoggedIn ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--color-primary)] flex items-center justify-center">
                    <span className="text-xs">{getInitials(username)}</span>
                  </div>
                  <span className="text-sm">{username}</span>
                </div>
                <Button variant="outline" onClick={onLogout}>
                  Logout
                </Button>
              </>
            ) : (
              <Button variant="primary" onClick={onLogin}>
                Login
              </Button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2 hover:bg-white/10 rounded-lg transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[var(--color-text-main)] border-t border-white/10">
          <div className="px-4 py-4 space-y-4">
            <button
              className={`block w-full text-left py-2 hover:text-gray-300 transition-colors ${currentView === 'dashboard' ? 'text-white border-l-2 border-white pl-2' : ''}`}
              onClick={() => {
                onNavigate?.('dashboard');
                setMobileMenuOpen(false);
              }}
            >
              Dashboard
            </button>
            <button
              className={`block w-full text-left py-2 hover:text-gray-300 transition-colors ${currentView === 'reports' ? 'text-white border-l-2 border-white pl-2' : ''}`}
              onClick={() => {
                onNavigate?.('reports');
                setMobileMenuOpen(false);
              }}
            >
              Reports
            </button>
            <button
              className={`block w-full text-left py-2 hover:text-gray-300 transition-colors ${currentView === 'admin' ? 'text-white border-l-2 border-white pl-2' : ''}`}
              onClick={() => {
                onNavigate?.('admin');
                setMobileMenuOpen(false);
              }}
            >
              Admin
            </button>
            
            {isLoggedIn ? (
              <div className="pt-4 border-t border-white/10 space-y-3">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-[var(--color-primary)] flex items-center justify-center">
                    <span className="text-xs">{getInitials(username)}</span>
                  </div>
                  <span className="text-sm">{username}</span>
                </div>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    onLogout?.();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full"
                >
                  Logout
                </Button>
              </div>
            ) : (
              <div className="pt-4 border-t border-white/10">
                <Button 
                  variant="primary" 
                  onClick={() => {
                    onLogin?.();
                    setMobileMenuOpen(false);
                  }}
                  className="w-full"
                >
                  Login
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}
