import React, { useState } from 'react';
import { MentionCard } from './MentionCard';
import { FileQuestion } from 'lucide-react';

interface Mention {
  id: string;
  sourceType: 'press' | 'social' | 'youtube';
  timestamp: string;
  title: string;
  url: string;
  company: string;
  source: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  isUrgent: boolean;
  excerpt: string;
}

interface MentionsListProps {
  mentions: Mention[];
}

export function MentionsList({ mentions }: MentionsListProps) {
  const [dateRange, setDateRange] = useState('24h');
  const [sentiment, setSentiment] = useState('all');
  const [urgentOnly, setUrgentOnly] = useState(false);

  // Filter mentions
  const filteredMentions = mentions.filter(mention => {
    if (urgentOnly && !mention.isUrgent) return false;
    if (sentiment !== 'all' && mention.sentiment !== sentiment) return false;
    return true;
  });

  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-sm">
      <div className="p-4 border-b border-[var(--color-border)]">
        <h2 className="mb-4">Latest mentions</h2>
        
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-3 py-2 border border-[var(--color-border)] rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>

          <select
            value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
            className="px-3 py-2 border border-[var(--color-border)] rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            <option value="all">All sentiment</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
            <option value="neutral">Neutral</option>
          </select>

          <label className="flex items-center gap-2 px-3 py-2 cursor-pointer">
            <input
              type="checkbox"
              checked={urgentOnly}
              onChange={(e) => setUrgentOnly(e.target.checked)}
              className="w-4 h-4 rounded border-[var(--color-border)] text-[var(--color-primary)] focus:ring-2 focus:ring-[var(--color-primary)]"
            />
            <span className="text-sm text-[var(--color-text-main)]">Urgent only</span>
          </label>
        </div>
      </div>

      {/* Mentions List */}
      <div className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
        {filteredMentions.length > 0 ? (
          filteredMentions.map(mention => (
            <MentionCard key={mention.id} {...mention} />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <FileQuestion className="w-12 h-12 text-[var(--color-text-secondary)] mb-3" />
            <p className="text-[var(--color-text-secondary)]">
              No mentions found for these filters
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
