import React, { useState } from 'react';
import { Settings, Users, Building2, Bell, Plus } from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';

export function AdminPage() {
  const [companies] = useState([
    { id: 1, name: 'TechCorp', sources: 245, status: 'active' },
    { id: 2, name: 'DataCo', sources: 189, status: 'active' },
    { id: 3, name: 'InnovateLab', sources: 156, status: 'active' },
    { id: 4, name: 'GreenEnergy Corp', sources: 134, status: 'paused' },
    { id: 5, name: 'FashionBrand', sources: 98, status: 'active' }
  ]);

  const [users] = useState([
    { id: 1, name: 'Sarah Johnson', email: 'sarah@company.com', role: 'Admin', lastActive: '2 hours ago' },
    { id: 2, name: 'Michael Chen', email: 'michael@company.com', role: 'Analyst', lastActive: '5 hours ago' },
    { id: 3, name: 'Emily Davis', email: 'emily@company.com', role: 'Viewer', lastActive: '1 day ago' }
  ]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Settings className="w-8 h-8 text-[var(--color-primary)]" />
          <h1>Admin Panel</h1>
        </div>
        <p className="text-[var(--color-text-secondary)]">
          Manage companies, users, and system settings
        </p>
      </div>

      {/* Settings Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer">
          <Building2 className="w-8 h-8 text-[var(--color-primary)] mb-3" />
          <h3 className="text-[var(--color-text-main)] mb-1">Companies</h3>
          <p className="text-2xl text-[var(--color-text-main)] mb-1">12</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Tracked companies</p>
        </div>

        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer">
          <Users className="w-8 h-8 text-[var(--color-primary)] mb-3" />
          <h3 className="text-[var(--color-text-main)] mb-1">Users</h3>
          <p className="text-2xl text-[var(--color-text-main)] mb-1">8</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Active users</p>
        </div>

        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer">
          <Bell className="w-8 h-8 text-[var(--color-primary)] mb-3" />
          <h3 className="text-[var(--color-text-main)] mb-1">Alert Rules</h3>
          <p className="text-2xl text-[var(--color-text-main)] mb-1">15</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Active rules</p>
        </div>

        <div className="bg-white border border-[var(--color-border)] rounded-lg p-6 hover:shadow-md transition-shadow cursor-pointer">
          <Settings className="w-8 h-8 text-[var(--color-primary)] mb-3" />
          <h3 className="text-[var(--color-text-main)] mb-1">Integrations</h3>
          <p className="text-2xl text-[var(--color-text-main)] mb-1">6</p>
          <p className="text-xs text-[var(--color-text-secondary)]">Connected services</p>
        </div>
      </div>

      {/* Companies Section */}
      <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-sm mb-6">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
          <h2>Tracked Companies</h2>
          <Button variant="primary">
            <Plus className="w-4 h-4" />
            Add Company
          </Button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[var(--color-hover-bg)]">
              <tr>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Company Name</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Sources</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Status</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {companies.map(company => (
                <tr key={company.id} className="border-t border-[var(--color-border)] hover:bg-[var(--color-hover-bg)] transition-colors">
                  <td className="px-4 py-3 text-sm text-[var(--color-text-main)]">{company.name}</td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{company.sources} sources</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs ${
                      company.status === 'active' 
                        ? 'bg-green-100 text-[var(--color-positive)]' 
                        : 'bg-gray-100 text-[var(--color-text-secondary)]'
                    }`}>
                      {company.status.charAt(0).toUpperCase() + company.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <Button variant="ghost" className="text-xs px-2 py-1">Edit</Button>
                      <Button variant="ghost" className="text-xs px-2 py-1">Delete</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Users Section */}
      <div className="bg-white border border-[var(--color-border)] rounded-lg shadow-sm">
        <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
          <h2>User Management</h2>
          <Button variant="primary">
            <Plus className="w-4 h-4" />
            Invite User
          </Button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-[var(--color-hover-bg)]">
              <tr>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Name</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Email</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Role</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Last Active</th>
                <th className="text-left px-4 py-3 text-xs text-[var(--color-text-secondary)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-t border-[var(--color-border)] hover:bg-[var(--color-hover-bg)] transition-colors">
                  <td className="px-4 py-3 text-sm text-[var(--color-text-main)]">{user.name}</td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs ${
                      user.role === 'Admin' 
                        ? 'bg-blue-100 text-[var(--color-primary)]' 
                        : user.role === 'Analyst'
                        ? 'bg-purple-100 text-purple-700'
                        : 'bg-gray-100 text-[var(--color-text-secondary)]'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{user.lastActive}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <Button variant="ghost" className="text-xs px-2 py-1">Edit</Button>
                      <Button variant="ghost" className="text-xs px-2 py-1">Remove</Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
