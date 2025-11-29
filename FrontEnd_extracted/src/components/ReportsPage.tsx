import React from 'react';
import { BarChart3, TrendingUp, FileText, Download } from 'lucide-react';
import { Button } from './Button';

export function ReportsPage() {
  const reports = [
    {
      id: 1,
      title: 'Weekly Media Summary',
      description: 'Comprehensive overview of all media mentions from the past week',
      date: 'Nov 22 - Nov 29, 2025',
      mentions: 1247,
      trend: '+12%'
    },
    {
      id: 2,
      title: 'Sentiment Analysis Report',
      description: 'Detailed breakdown of sentiment across all tracked companies',
      date: 'November 2025',
      mentions: 4582,
      trend: '+8%'
    },
    {
      id: 3,
      title: 'Source Distribution',
      description: 'Analysis of mention distribution across press, social, and video platforms',
      date: 'November 2025',
      mentions: 4582,
      trend: '-3%'
    },
    {
      id: 4,
      title: 'Urgent Alerts Summary',
      description: 'Critical mentions that required immediate attention this month',
      date: 'November 2025',
      mentions: 23,
      trend: '+15%'
    }
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <FileText className="w-8 h-8 text-[var(--color-primary)]" />
          <h1>Reports</h1>
        </div>
        <p className="text-[var(--color-text-secondary)]">
          Generate and download comprehensive media monitoring reports
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--color-text-secondary)]">Total Reports</p>
            <FileText className="w-4 h-4 text-[var(--color-primary)]" />
          </div>
          <p className="text-2xl text-[var(--color-text-main)]">24</p>
        </div>
        
        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--color-text-secondary)]">This Month</p>
            <BarChart3 className="w-4 h-4 text-[var(--color-primary)]" />
          </div>
          <p className="text-2xl text-[var(--color-text-main)]">8</p>
        </div>
        
        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-[var(--color-text-secondary)]">Avg. Response Time</p>
            <TrendingUp className="w-4 h-4 text-[var(--color-positive)]" />
          </div>
          <p className="text-2xl text-[var(--color-text-main)]">2.4h</p>
        </div>
      </div>

      {/* Reports List */}
      <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-sm">
        <div className="p-4 border-b border-[var(--color-border)]">
          <h2>Available Reports</h2>
        </div>
        
        <div className="divide-y divide-[var(--color-border)]">
          {reports.map(report => (
            <div key={report.id} className="p-6 hover:bg-[var(--color-hover-bg)] transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex-1">
                  <h3 className="text-[var(--color-text-main)] mb-1">{report.title}</h3>
                  <p className="text-sm text-[var(--color-text-secondary)] mb-2">
                    {report.description}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-[var(--color-text-secondary)]">
                    <span>{report.date}</span>
                    <span>•</span>
                    <span>{report.mentions.toLocaleString()} mentions</span>
                    <span>•</span>
                    <span className={report.trend.startsWith('+') ? 'text-[var(--color-positive)]' : 'text-[var(--color-urgent)]'}>
                      {report.trend} vs. previous period
                    </span>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  <Button variant="secondary">
                    View
                  </Button>
                  <Button variant="primary">
                    <Download className="w-4 h-4" />
                    Download
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Generate New Report */}
      <div className="mt-6 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-[var(--color-text-main)] mb-1">Generate Custom Report</h3>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Create a custom report with your own date range and filters
            </p>
          </div>
          <Button variant="primary">
            <BarChart3 className="w-4 h-4" />
            New Report
          </Button>
        </div>
      </div>
    </div>
  );
}
