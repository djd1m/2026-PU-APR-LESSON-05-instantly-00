import { useState, useEffect } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const defaultForm = {
  provider: 'resend',
  from_email: '',
  daily_limit: '50',
  smtp_host: '',
  smtp_port: '587',
  smtp_user: '',
  smtp_password: '',
  api_key: '',
};

export default function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [form, setForm] = useState({ ...defaultForm });

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      const data = await api.get('/accounts');
      setAccounts(data);
    } catch (err) {
      toast.error(err.detail || 'Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleAdd = async (e) => {
    e.preventDefault();
    const payload = {
      provider: form.provider,
      from_email: form.from_email,
      daily_limit: Number(form.daily_limit),
    };
    if (form.provider === 'smtp') {
      payload.smtp_host = form.smtp_host;
      payload.smtp_port = Number(form.smtp_port);
      payload.smtp_user = form.smtp_user;
      payload.smtp_password = form.smtp_password;
    } else {
      payload.api_key = form.api_key;
    }
    try {
      await api.post('/accounts', payload);
      toast.success('Account added successfully');
      setShowAddModal(false);
      setForm({ ...defaultForm });
      fetchAccounts();
    } catch (err) {
      toast.error(err.detail || 'Failed to add account');
    }
  };

  const handleToggleActive = async (account) => {
    try {
      await api.put(`/accounts/${account.id}`, { is_active: !account.is_active });
      toast.success(account.is_active ? 'Account paused' : 'Account activated');
      fetchAccounts();
    } catch (err) {
      toast.error(err.detail || 'Failed to update account');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this account?')) return;
    try {
      await api.del(`/accounts/${id}`);
      toast.success('Account deleted');
      fetchAccounts();
    } catch (err) {
      toast.error(err.detail || 'Failed to delete account');
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Email Accounts</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          <PlusIcon className="w-4 h-4" />
          Add Account
        </button>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-12">Loading accounts...</div>
      ) : accounts.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center text-gray-500">
          No email accounts yet. Add your first account to start sending.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {accounts.map((account) => {
            const sentPercent = account.daily_limit
              ? Math.min((account.sent_today / account.daily_limit) * 100, 100)
              : 0;
            const isResend = account.provider === 'resend';

            return (
              <div
                key={account.id}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900 truncate">{account.from_email}</span>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                      isResend ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {isResend ? 'Resend' : 'SMTP'}
                    </span>
                    <StatusBadge status={account.is_active ? 'active' : 'paused'} />
                  </div>
                </div>
                {!isResend && (
                  <>
                    <p className="text-sm text-gray-500 mt-1">
                      {account.smtp_host}:{account.smtp_port}
                    </p>
                    <p className="text-sm text-gray-500">{account.smtp_user}</p>
                  </>
                )}
                {isResend && (
                  <p className="text-sm text-gray-500 mt-1">Resend API</p>
                )}

                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-500">Sent Today</span>
                    <span className="font-medium text-gray-900">
                      {account.sent_today}/{account.daily_limit}
                    </span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-indigo-600 rounded-full transition-all"
                      style={{ width: `${sentPercent}%` }}
                    />
                  </div>
                </div>

                {!isResend && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">Warmup</span>
                      <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                        account.warmup_status === 'warming' ? 'bg-amber-100 text-amber-700' :
                        account.warmup_status === 'ready' ? 'bg-green-100 text-green-700' :
                        account.warmup_status === 'paused' ? 'bg-red-100 text-red-600' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {account.warmup_status === 'warming' ? 'Warming Up' :
                         account.warmup_status === 'ready' ? 'Ready' :
                         account.warmup_status === 'paused' ? 'Paused' :
                         'Not Started'}
                      </span>
                    </div>

                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>Day {account.warmup_day || 0} of 14</span>
                      <span>Target: {account.warmup_daily_target || 0} emails/day</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-3">
                      <div
                        className={`h-full rounded-full transition-all ${
                          account.warmup_status === 'ready' ? 'bg-green-500' : 'bg-amber-500'
                        }`}
                        style={{ width: `${Math.min(((account.warmup_day || 0) / 14) * 100, 100)}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-gray-500">Score</span>
                      <span className="text-lg font-bold text-gray-900">{account.warmup_score || 0}%</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          account.warmup_status === 'ready' ? 'bg-green-500' : 'bg-amber-500'
                        }`}
                        style={{ width: `${account.warmup_score || 0}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="mt-4 flex gap-2 flex-wrap">
                  <button
                    onClick={() => handleToggleActive(account)}
                    className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-3 py-1.5 rounded-lg text-xs font-medium flex-1"
                  >
                    {account.is_active ? 'Pause' : 'Activate'}
                  </button>
                  {!isResend && (account.warmup_status === 'new' || account.warmup_status === 'paused' || !account.warmup_status) && (
                    <button
                      onClick={async () => {
                        try {
                          await api.post(`/accounts/${account.id}/warmup/start`);
                          toast.success('Warmup started!');
                          fetchAccounts();
                        } catch (err) {
                          toast.error(err.detail || 'Failed to start warmup');
                        }
                      }}
                      className="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1.5 rounded-lg text-xs font-medium"
                    >
                      Start Warmup
                    </button>
                  )}
                  {!isResend && account.warmup_status === 'warming' && (
                    <>
                      <button
                        onClick={async () => {
                          try {
                            await api.post(`/accounts/${account.id}/warmup/pause`);
                            toast.success('Warmup paused');
                            fetchAccounts();
                          } catch (err) {
                            toast.error(err.detail || 'Failed to pause warmup');
                          }
                        }}
                        className="bg-amber-100 text-amber-700 px-3 py-1.5 rounded-lg text-xs font-medium"
                      >
                        Pause
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await api.post(`/accounts/${account.id}/warmup/advance`);
                            toast.success('Day advanced!');
                            fetchAccounts();
                          } catch (err) {
                            toast.error(err.detail || 'Failed to advance day');
                          }
                        }}
                        className="bg-indigo-100 text-indigo-700 px-3 py-1.5 rounded-lg text-xs font-medium"
                      >
                        Advance Day
                      </button>
                    </>
                  )}
                  {!isResend && account.warmup_status === 'ready' && (
                    <span className="inline-flex items-center gap-1 bg-green-100 text-green-700 px-3 py-1.5 rounded-lg text-xs font-medium">
                      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      Warmup Complete
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(account.id)}
                    className="bg-white border border-red-200 text-red-500 hover:bg-red-50 px-3 py-1.5 rounded-lg text-xs font-medium"
                  >
                    <TrashIcon className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add Email Account">
        <form onSubmit={handleAdd} className="space-y-4">
          {/* Provider selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setForm({ ...form, provider: 'resend' })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  form.provider === 'resend'
                    ? 'border-indigo-600 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-semibold text-sm text-gray-900">Resend</div>
                <div className="text-xs text-gray-500 mt-1">Just API key — easy setup</div>
              </button>
              <button
                type="button"
                onClick={() => setForm({ ...form, provider: 'smtp' })}
                className={`p-4 rounded-lg border-2 text-center transition-all ${
                  form.provider === 'smtp'
                    ? 'border-indigo-600 bg-indigo-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="font-semibold text-sm text-gray-900">SMTP</div>
                <div className="text-xs text-gray-500 mt-1">Custom SMTP server</div>
              </button>
            </div>
          </div>

          {/* From Email — always required */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Email *</label>
            <input
              type="email"
              value={form.from_email}
              onChange={(e) => setForm({ ...form, from_email: e.target.value })}
              required
              placeholder={form.provider === 'resend' ? 'you@yourdomain.com' : 'outreach@company.com'}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
            {form.provider === 'resend' && (
              <p className="text-xs text-gray-500 mt-1">
                Use your verified domain or onboarding@resend.dev for testing
              </p>
            )}
          </div>

          {/* Resend fields */}
          {form.provider === 'resend' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Resend API Key *</label>
              <input
                type="password"
                value={form.api_key}
                onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                required
                placeholder="re_xxxxxxxxx..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <p className="text-xs text-gray-500 mt-1">
                Get your API key at{' '}
                <a href="https://resend.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-500">
                  resend.com/api-keys
                </a>
              </p>
            </div>
          )}

          {/* SMTP fields */}
          {form.provider === 'smtp' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Host *</label>
                <input
                  type="text"
                  value={form.smtp_host}
                  onChange={(e) => setForm({ ...form, smtp_host: e.target.value })}
                  required
                  placeholder="smtp.gmail.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Port</label>
                <input
                  type="number"
                  value={form.smtp_port}
                  onChange={(e) => setForm({ ...form, smtp_port: e.target.value })}
                  placeholder="587"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP User *</label>
                <input
                  type="text"
                  value={form.smtp_user}
                  onChange={(e) => setForm({ ...form, smtp_user: e.target.value })}
                  required
                  placeholder="user@gmail.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP Password *</label>
                <input
                  type="password"
                  value={form.smtp_password}
                  onChange={(e) => setForm({ ...form, smtp_password: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
            </>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Daily Limit</label>
            <input
              type="number"
              value={form.daily_limit}
              onChange={(e) => setForm({ ...form, daily_limit: e.target.value })}
              placeholder="50"
              min="1"
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
              Add Account
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
