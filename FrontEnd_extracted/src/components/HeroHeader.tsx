import React from 'react';
import { BarChart3 } from 'lucide-react';

export function HeroHeader() {
  return (
    <div className="bg-white border-b border-[var(--color-border)] px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex-1">
            <h1 className="mb-2">Media Monitoring Dashboard</h1>
            <p className="text-[var(--color-text-secondary)]">
              Aggregates live mentions, sources, and urgent alerts.
            </p>
          </div>
          <div className="flex-shrink-0">
            <div className="w-16 h-16 bg-gradient-to-br from-[var(--color-primary)] to-[var(--color-primary-hover)] rounded-lg flex items-center justify-center shadow-lg">
              <BarChart3 className="w-8 h-8 text-white" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
