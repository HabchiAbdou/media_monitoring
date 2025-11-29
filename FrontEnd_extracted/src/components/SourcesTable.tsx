import React from 'react';
import { Badge } from './Badge';
import { ChevronRight } from 'lucide-react';

interface SourceRow {
  sourceType: 'press' | 'social' | 'youtube';
  sources: number;
  mentions: number;
  urgent: number;
}

interface SourcesTableProps {
  data: SourceRow[];
  onRowClick?: (sourceType: string) => void;
}

export function SourcesTable({ data, onRowClick }: SourcesTableProps) {
  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg overflow-hidden shadow-sm">
      <div className="p-4 border-b border-[var(--color-border)]">
        <h2>Sources overview</h2>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[var(--color-hover-bg)]">
            <tr>
              <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">
                Source type
              </th>
              <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">
                Sources
              </th>
              <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">
                Mentions
              </th>
              <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">
                Urgent
              </th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, index) => (
              <tr
                key={row.sourceType}
                className="border-t border-[var(--color-border)] hover:bg-[var(--color-hover-bg)] cursor-pointer transition-colors"
                onClick={() => onRowClick?.(row.sourceType)}
              >
                <td className="px-4 py-3">
                  <Badge variant={row.sourceType}>
                    {row.sourceType.charAt(0).toUpperCase() + row.sourceType.slice(1)}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-main)]">
                  {row.sources}
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-main)]">
                  {row.mentions.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span className={`text-sm ${row.urgent > 0 ? 'text-[var(--color-urgent)]' : 'text-[var(--color-text-secondary)]'}`}>
                    {row.urgent}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <ChevronRight className="w-4 h-4 text-[var(--color-text-secondary)]" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
