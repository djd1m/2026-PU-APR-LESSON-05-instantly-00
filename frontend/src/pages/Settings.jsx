import { useState, useEffect } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import { KeyIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mailiveryKey, setMailiveryKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [showMailivery, setShowMailivery] = useState(false);
  const [showOpenai, setShowOpenai] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await api.get('/settings');
      setSettings(data);
    } catch (err) {
      toast.error(err.detail || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (field) => {
    setSaving(true);
    const payload = {};
    if (field === 'mailivery') {
      payload.mailivery_api_key = mailiveryKey;
    } else if (field === 'openai') {
      payload.openai_api_key = openaiKey;
    }

    try {
      const data = await api.put('/settings', payload);
      setSettings(data);
      setMailiveryKey('');
      setOpenaiKey('');
      setShowMailivery(false);
      setShowOpenai(false);
      toast.success('API key saved');
    } catch (err) {
      toast.error(err.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (field) => {
    if (!window.confirm('Remove this API key?')) return;
    setSaving(true);
    const payload = {};
    if (field === 'mailivery') payload.mailivery_api_key = '';
    if (field === 'openai') payload.openai_api_key = '';

    try {
      const data = await api.put('/settings', payload);
      setSettings(data);
      toast.success('API key removed');
    } catch (err) {
      toast.error(err.detail || 'Failed to remove key');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500 mt-1">Manage API keys and integrations</p>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* Mailivery API Key */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-50 rounded-lg">
                <KeyIcon className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">Mailivery API Key</h3>
                <p className="text-sm text-gray-500">Email warmup through Mailivery peer network</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {settings?.mailivery_api_key_set ? (
                <span className="inline-flex items-center gap-1 text-green-700 text-sm">
                  <CheckCircleIcon className="w-4 h-4" />
                  Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-gray-400 text-sm">
                  <XCircleIcon className="w-4 h-4" />
                  Not set
                </span>
              )}
            </div>
          </div>

          {settings?.mailivery_api_key_set && !showMailivery && (
            <div className="mt-4 flex items-center gap-3">
              <code className="bg-gray-50 px-3 py-1.5 rounded text-sm text-gray-600 font-mono">
                {settings.mailivery_api_key_preview}
              </code>
              <button
                onClick={() => setShowMailivery(true)}
                className="text-indigo-600 hover:text-indigo-500 text-sm font-medium"
              >
                Change
              </button>
              <button
                onClick={() => handleRemove('mailivery')}
                className="text-red-500 hover:text-red-600 text-sm font-medium"
              >
                Remove
              </button>
            </div>
          )}

          {(!settings?.mailivery_api_key_set || showMailivery) && (
            <div className="mt-4">
              <div className="flex gap-2">
                <input
                  type="password"
                  value={mailiveryKey}
                  onChange={(e) => setMailiveryKey(e.target.value)}
                  placeholder="Enter Mailivery API key..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none font-mono"
                />
                <button
                  onClick={() => handleSave('mailivery')}
                  disabled={!mailiveryKey || saving}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Get your API key at{' '}
                <a href="https://mailivery.io" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-500">
                  mailivery.io
                </a>
                {' '}— from $49/mo for unlimited mailboxes
              </p>
            </div>
          )}
        </div>

        {/* OpenAI API Key */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg">
                <KeyIcon className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="font-medium text-gray-900">OpenAI API Key</h3>
                <p className="text-sm text-gray-500">AI-powered email personalization (GPT-4)</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {settings?.openai_api_key_set ? (
                <span className="inline-flex items-center gap-1 text-green-700 text-sm">
                  <CheckCircleIcon className="w-4 h-4" />
                  Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-gray-400 text-sm">
                  <XCircleIcon className="w-4 h-4" />
                  Not set
                </span>
              )}
            </div>
          </div>

          {settings?.openai_api_key_set && !showOpenai && (
            <div className="mt-4 flex items-center gap-3">
              <code className="bg-gray-50 px-3 py-1.5 rounded text-sm text-gray-600 font-mono">
                {settings.openai_api_key_preview}
              </code>
              <button
                onClick={() => setShowOpenai(true)}
                className="text-indigo-600 hover:text-indigo-500 text-sm font-medium"
              >
                Change
              </button>
              <button
                onClick={() => handleRemove('openai')}
                className="text-red-500 hover:text-red-600 text-sm font-medium"
              >
                Remove
              </button>
            </div>
          )}

          {(!settings?.openai_api_key_set || showOpenai) && (
            <div className="mt-4">
              <div className="flex gap-2">
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none font-mono"
                />
                <button
                  onClick={() => handleSave('openai')}
                  disabled={!openaiKey || saving}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Get your API key at{' '}
                <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-500">
                  platform.openai.com/api-keys
                </a>
              </p>
            </div>
          )}
        </div>

        {/* Info box */}
        <div className="bg-indigo-50 rounded-xl p-4">
          <p className="text-sm text-indigo-700">
            API keys are stored securely per-user and never shown in full after saving.
            If no key is set here, the system falls back to server-level environment variables.
          </p>
        </div>
      </div>
    </div>
  );
}
