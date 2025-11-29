import React from 'react';
import { Badge } from './Badge';

interface MentionCardProps {
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

export function MentionCard({
  sourceType,
  timestamp,
  title,
  url,
  company,
  source,
  sentiment,
  isUrgent,
  excerpt
}: MentionCardProps) {
  return (
    <div className={`p-4 border rounded-lg transition-colors ${
      isUrgent 
        ? 'bg-[var(--color-urgent-light)] border-[var(--color-urgent)]' 
        : 'bg-white border-[var(--color-border)] hover:border-[var(--color-primary)]'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Badge variant={sourceType}>
          {sourceType.charAt(0).toUpperCase() + sourceType.slice(1)}
        </Badge>
        <span className="text-xs text-[var(--color-text-secondary)]">{timestamp}</span>
      </div>

      {/* Title */}
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[var(--color-primary)] hover:underline block mb-2"
      >
        {title}
      </a>

      {/* Meta */}
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className="text-xs text-[var(--color-text-secondary)]">{company}</span>
        <span className="text-xs text-[var(--color-text-secondary)]">·</span>
        <span className="text-xs text-[var(--color-text-secondary)]">{source}</span>
        <span className="text-xs text-[var(--color-text-secondary)]">·</span>
        <Badge variant={sentiment}>
          {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
        </Badge>
        {isUrgent && <Badge variant="urgent">URGENT</Badge>}
      </div>

      {/* Excerpt */}
      <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">{excerpt}</p>
    </div>
  );
}
