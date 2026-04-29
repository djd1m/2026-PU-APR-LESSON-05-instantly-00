import { useState, useEffect } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { TrashIcon, PlusIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const STATUSES = ['new', 'contacted', 'replied', 'bounced', 'unsubscribed'];

export default function Leads() {
  const [leads, setLeads] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [campaignFilter, setCampaignFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [bulkText, setBulkText] = useState('');
  const [bulkCampaignId, setBulkCampaignId] = useState('');
  const [bulkPreview, setBulkPreview] = useState(null);
  const [bulkResult, setBulkResult] = useState(null);
  const [addForm, setAddForm] = useState({
    campaign_id: '',
    email: '',
    first_name: '',
    last_name: '',
    company: '',
  });

  const fetchLeads = async (campaignId, status) => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (campaignId) params.append('campaign_id', campaignId);
      if (status) params.append('status', status);
      const query = params.toString();
      const data = await api.get(`/leads${query ? `?${query}` : ''}`);
      setLeads(data);
    } catch (err) {
      toast.error(err.detail || 'Failed to load leads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const [campaignData] = await Promise.all([
          api.get('/campaigns'),
        ]);
        setCampaigns(campaignData);
      } catch (err) {
        toast.error(err.detail || 'Failed to load campaigns');
      }
      fetchLeads('', '');
    };
    init();
  }, []);

  const handleCampaignFilterChange = (value) => {
    setCampaignFilter(value);
    fetchLeads(value, statusFilter);
  };

  const handleStatusFilterChange = (value) => {
    setStatusFilter(value);
    fetchLeads(campaignFilter, value);
  };

  const getCampaignName = (campaignId) => {
    const campaign = campaigns.find((c) => c.id === campaignId);
    return campaign ? campaign.name : '-';
  };

  const handleAddLead = async (e) => {
    e.preventDefault();
    try {
      await api.post('/leads', {
        ...addForm,
        campaign_id: addForm.campaign_id,
      });
      toast.success('Lead added successfully');
      setShowAddModal(false);
      setAddForm({ campaign_id: '', email: '', first_name: '', last_name: '', company: '' });
      fetchLeads(campaignFilter, statusFilter);
    } catch (err) {
      toast.error(err.detail || 'Failed to add lead');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    try {
      await api.del(`/leads/${id}`);
      toast.success('Lead deleted');
      fetchLeads(campaignFilter, statusFilter);
    } catch (err) {
      toast.error(err.detail || 'Failed to delete lead');
    }
  };

  const parseBulkCsv = () => {
    const lines = bulkText.trim().split('\n').filter(Boolean);
    const parsed = [];
    for (const line of lines) {
      const parts = line.split(',').map((s) => s.trim());
      if (!parts[0] || !parts[0].includes('@')) continue;
      parsed.push({
        email: parts[0],
        first_name: parts[1] || '',
        last_name: parts[2] || '',
        company: parts[3] || '',
      });
    }
    setBulkPreview(parsed);
    setBulkResult(null);
  };

  const [bulkLoading, setBulkLoading] = useState(false);

  const handleBulkImport = async () => {
    if (!bulkCampaignId || !bulkPreview || bulkPreview.length === 0) return;
    setBulkLoading(true);
    try {
      const result = await api.post('/leads/bulk', {
        campaign_id: bulkCampaignId,
        leads: bulkPreview.map((l) => ({ ...l, campaign_id: bulkCampaignId })),
      });
      setBulkResult(result);
      toast.success(`Imported ${result.imported} leads`);
      fetchLeads(campaignFilter, statusFilter);
    } catch (err) {
      toast.error(err.detail || 'Bulk import failed');
    } finally {
      setBulkLoading(false);
    }
  };

  const closeBulkModal = () => {
    setShowBulkModal(false);
    setBulkText('');
    setBulkCampaignId('');
    setBulkPreview(null);
    setBulkResult(null);
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Leads</h1>
        <div className="flex gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
          >
            <PlusIcon className="w-4 h-4" />
            Add Lead
          </button>
          <button
            onClick={() => setShowBulkModal(true)}
            className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2"
          >
            <ArrowUpTrayIcon className="w-4 h-4" />
            Bulk Import
          </button>
        </div>
      </div>

      <div className="flex gap-4 mb-6">
        <select
          value={campaignFilter}
          onChange={(e) => handleCampaignFilterChange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
        >
          <option value="">All Campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => handleStatusFilterChange(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
        >
          <option value="">All Statuses</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading leads...</div>
        ) : leads.length === 0 ? (
          <div className="p-12 text-center text-gray-500">
            No leads found. Add leads to get started.
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Campaign
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900">{lead.email}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {[lead.first_name, lead.last_name].filter(Boolean).join(' ') || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">{lead.company || '-'}</td>
                  <td className="px-6 py-4 text-sm">
                    <StatusBadge status={lead.status} />
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {getCampaignName(lead.campaign_id)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-right">
                    <button
                      onClick={() => handleDelete(lead.id)}
                      className="text-red-400 hover:text-red-600 transition-colors"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add Lead">
        <form onSubmit={handleAddLead} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Campaign *</label>
            <select
              value={addForm.campaign_id}
              onChange={(e) => setAddForm({ ...addForm, campaign_id: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            >
              <option value="">Select campaign...</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={addForm.email}
              onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">First Name</label>
            <input
              type="text"
              value={addForm.first_name}
              onChange={(e) => setAddForm({ ...addForm, first_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Last Name</label>
            <input
              type="text"
              value={addForm.last_name}
              onChange={(e) => setAddForm({ ...addForm, last_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
            <input
              type="text"
              value={addForm.company}
              onChange={(e) => setAddForm({ ...addForm, company: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => setShowAddModal(false)}
              className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Add Lead
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={showBulkModal} onClose={closeBulkModal} title="Bulk Import Leads" maxWidth="max-w-2xl">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Campaign *</label>
            <select
              value={bulkCampaignId}
              onChange={(e) => setBulkCampaignId(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            >
              <option value="">Select campaign...</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CSV Data</label>
            <textarea
              value={bulkText}
              onChange={(e) => {
                setBulkText(e.target.value);
                setBulkPreview(null);
                setBulkResult(null);
              }}
              rows={8}
              placeholder={'email,first_name,last_name,company\njohn@example.com,John,Doe,Acme Inc'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none font-mono"
            />
          </div>
          <button
            type="button"
            onClick={parseBulkCsv}
            disabled={!bulkText.trim()}
            className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            Parse CSV
          </button>
          {bulkPreview && (
            <div className="bg-gray-50 rounded-lg p-4 text-sm">
              <p className="font-medium text-gray-900">Found {bulkPreview.length} leads</p>
              {bulkPreview.length > 0 && (
                <ul className="mt-2 space-y-1 text-gray-600 max-h-32 overflow-y-auto">
                  {bulkPreview.slice(0, 10).map((l, i) => (
                    <li key={i}>
                      {l.email} {l.first_name && `- ${l.first_name} ${l.last_name}`} {l.company && `(${l.company})`}
                    </li>
                  ))}
                  {bulkPreview.length > 10 && <li>...and {bulkPreview.length - 10} more</li>}
                </ul>
              )}
            </div>
          )}
          {bulkResult && (
            <div className="bg-green-50 rounded-lg p-4 text-sm text-green-800">
              Imported: {bulkResult.imported}, Skipped: {bulkResult.skipped}
              {bulkResult.errors > 0 && `, Errors: ${bulkResult.errors}`}
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={closeBulkModal}
              className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Close
            </button>
            <button
              type="button"
              onClick={handleBulkImport}
              disabled={!bulkPreview || bulkPreview.length === 0 || !bulkCampaignId || bulkLoading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {bulkLoading ? 'Importing...' : 'Import'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
