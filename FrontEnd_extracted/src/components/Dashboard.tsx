import React, { useState } from 'react';
import { Navbar } from './Navbar';
import { HeroHeader } from './HeroHeader';
import { MetricCard } from './MetricCard';
import { SourcesTable } from './SourcesTable';
import { MentionsList } from './MentionsList';
import { AlertBar } from './AlertBar';
import { ReportsPage } from './ReportsPage';
import { AdminPage } from './AdminPage';

interface DashboardProps {
  username: string;
  currentView: string;
  onLogout: () => void;
  onNavigate: (view: string) => void;
}

export function Dashboard({ username, currentView, onLogout, onNavigate }: DashboardProps) {
  const [alert, setAlert] = useState<{ variant: 'info' | 'success' | 'error'; message: string } | null>({
    variant: 'success',
    message: 'Welcome back! You have 8 new urgent alerts that require attention.'
  });

  // Mock data for sources table
  const sourcesData = [
    { sourceType: 'press' as const, sources: 245, mentions: 2341, urgent: 3 },
    { sourceType: 'social' as const, sources: 1829, mentions: 1956, urgent: 5 },
    { sourceType: 'youtube' as const, sources: 89, mentions: 285, urgent: 0 }
  ];

  // Mock data for mentions
  const mentionsData = [
    {
      id: '1',
      sourceType: 'press' as const,
      timestamp: '2 hours ago',
      title: 'TechCorp Announces Major Partnership with Global Retailer',
      url: '#',
      company: 'TechCorp',
      source: 'Tech News Daily',
      sentiment: 'positive' as const,
      isUrgent: false,
      excerpt: 'In a groundbreaking move, TechCorp has announced a strategic partnership that will revolutionize the retail technology landscape...'
    },
    {
      id: '2',
      sourceType: 'social' as const,
      timestamp: '3 hours ago',
      title: 'Customer complaints surge on Twitter regarding DataCo service outage',
      url: '#',
      company: 'DataCo',
      source: 'Twitter',
      sentiment: 'negative' as const,
      isUrgent: true,
      excerpt: 'Multiple users are reporting widespread service disruptions affecting business operations across North America and Europe...'
    },
    {
      id: '3',
      sourceType: 'youtube' as const,
      timestamp: '5 hours ago',
      title: 'InnovateLab CEO discusses future of AI in healthcare',
      url: '#',
      company: 'InnovateLab',
      source: 'Tech Insights Channel',
      sentiment: 'neutral' as const,
      isUrgent: false,
      excerpt: 'The CEO shares insights on how artificial intelligence will transform patient care and medical diagnostics over the next decade...'
    },
    {
      id: '4',
      sourceType: 'press' as const,
      timestamp: '6 hours ago',
      title: 'GreenEnergy Corp faces regulatory investigation',
      url: '#',
      company: 'GreenEnergy Corp',
      source: 'Business Times',
      sentiment: 'negative' as const,
      isUrgent: true,
      excerpt: 'Federal regulators have launched an investigation into the company\'s environmental compliance practices...'
    },
    {
      id: '5',
      sourceType: 'social' as const,
      timestamp: '8 hours ago',
      title: 'FashionBrand trending after celebrity endorsement',
      url: '#',
      company: 'FashionBrand',
      source: 'Instagram',
      sentiment: 'positive' as const,
      isUrgent: false,
      excerpt: 'The brand has seen a massive surge in social media engagement following a high-profile celebrity collaboration announcement...'
    },
    {
      id: '6',
      sourceType: 'press' as const,
      timestamp: '10 hours ago',
      title: 'FinTech Solutions reports record quarterly earnings',
      url: '#',
      company: 'FinTech Solutions',
      source: 'Financial Post',
      sentiment: 'positive' as const,
      isUrgent: false,
      excerpt: 'The financial technology company exceeded analyst expectations with a 45% year-over-year revenue growth...'
    },
    {
      id: '7',
      sourceType: 'youtube' as const,
      timestamp: '12 hours ago',
      title: 'AutoDrive safety concerns raised by consumer advocacy group',
      url: '#',
      company: 'AutoDrive',
      source: 'Consumer Reports',
      sentiment: 'negative' as const,
      isUrgent: true,
      excerpt: 'A leading consumer advocacy organization has published findings questioning the safety features of the company\'s latest autonomous vehicle...'
    },
    {
      id: '8',
      sourceType: 'social' as const,
      timestamp: '14 hours ago',
      title: 'GameStudio announces surprise game reveal at upcoming conference',
      url: '#',
      company: 'GameStudio',
      source: 'Reddit',
      sentiment: 'positive' as const,
      isUrgent: false,
      excerpt: 'Gaming community buzzes with excitement after the studio teased a major announcement for their long-awaited franchise sequel...'
    }
  ];

  const handleSourceClick = (sourceType: string) => {
    setAlert({
      variant: 'info',
      message: `Filtering mentions by ${sourceType} sources...`
    });
    
    // Auto-hide after 3 seconds
    setTimeout(() => setAlert(null), 3000);
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <Navbar 
        isLoggedIn={true} 
        username={username} 
        currentView={currentView}
        onLogout={onLogout}
        onNavigate={onNavigate}
      />
      
      {/* Alert */}
      {alert && (
        <AlertBar
          variant={alert.variant}
          message={alert.message}
          onClose={() => setAlert(null)}
        />
      )}
      
      {currentView === 'dashboard' && (
        <>
          <HeroHeader />
          
          {/* Main Content */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            {/* Stats Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
              <MetricCard title="Companies" value={12} label="Tracked" />
              <MetricCard title="Mentions" value={4582} label="This period" />
              <MetricCard title="Urgent alerts" value={8} label="Critical" isUrgent={true} />
            </div>

            {/* Two-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              {/* Left column - 40% on desktop */}
              <div className="lg:col-span-2">
                <SourcesTable data={sourcesData} onRowClick={handleSourceClick} />
              </div>

              {/* Right column - 60% on desktop */}
              <div className="lg:col-span-3">
                <MentionsList mentions={mentionsData} />
              </div>
            </div>
          </div>
        </>
      )}
      
      {currentView === 'reports' && <ReportsPage />}
      
      {currentView === 'admin' && <AdminPage />}
    </div>
  );
}
