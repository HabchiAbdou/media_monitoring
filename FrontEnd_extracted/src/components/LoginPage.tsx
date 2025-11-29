import React, { useState } from 'react';
import { Button } from './Button';
import { Radio, AlertCircle } from 'lucide-react';

interface LoginPageProps {
  onLogin: (username: string, password: string) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<{ username?: string; password?: string }>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const newErrors: { username?: string; password?: string } = {};
    
    if (!username.trim()) {
      newErrors.username = 'Username is required';
    }
    
    if (!password.trim()) {
      newErrors.password = 'Password is required';
    }
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    setErrors({});
    onLogin(username, password);
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-lg shadow-lg border border-[var(--color-border)] p-8">
          {/* Logo and Title */}
          <div className="flex flex-col items-center mb-8">
            <div className="w-12 h-12 bg-[var(--color-primary)] rounded-lg flex items-center justify-center mb-4">
              <Radio className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-[var(--color-text-main)] mb-1">Media Monitor</h1>
            <h2 className="text-[var(--color-text-main)]">Sign in</h2>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block mb-2 text-[var(--color-text-main)]">
                Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (errors.username) {
                    setErrors({ ...errors, username: undefined });
                  }
                }}
                className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-colors ${
                  errors.username
                    ? 'border-[var(--color-urgent)] focus:ring-[var(--color-urgent)]'
                    : 'border-[var(--color-border)] focus:ring-[var(--color-primary)]'
                }`}
                placeholder="Enter your username"
              />
              {errors.username && (
                <div className="flex items-center gap-1 mt-1 text-[var(--color-urgent)] text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.username}</span>
                </div>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block mb-2 text-[var(--color-text-main)]">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) {
                    setErrors({ ...errors, password: undefined });
                  }
                }}
                className={`w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-colors ${
                  errors.password
                    ? 'border-[var(--color-urgent)] focus:ring-[var(--color-urgent)]'
                    : 'border-[var(--color-border)] focus:ring-[var(--color-primary)]'
                }`}
                placeholder="Enter your password"
              />
              {errors.password && (
                <div className="flex items-center gap-1 mt-1 text-[var(--color-urgent)] text-xs">
                  <AlertCircle className="w-3 h-3" />
                  <span>{errors.password}</span>
                </div>
              )}
            </div>

            {/* Submit Button */}
            <Button type="submit" variant="primary" className="w-full">
              Login
            </Button>

            {/* Forgot Password Link */}
            <div className="text-center">
              <a
                href="#forgot"
                className="text-sm text-[var(--color-primary)] hover:underline"
              >
                Forgot password?
              </a>
            </div>
          </form>
        </div>

        {/* Demo Credentials */}
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800">
            <strong>Demo credentials:</strong> Use any username and password to login
          </p>
        </div>
      </div>
    </div>
  );
}
