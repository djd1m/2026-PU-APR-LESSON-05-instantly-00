import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import toast from 'react-hot-toast';

export default function CampaignForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [form, setForm] = useState({
    name: '',
    from_name: '',
    from_email: '',
    subject_template: '',
    body_template: '',
    ai_personalization_enabled: false,
  });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(isEdit);

  useEffect(() => {
    if (!isEdit) return;
    async function fetchCampaign() {
      try {
        const res = await api.get(`/campaigns/${id}`);
        const c = res;
        setForm({
          name: c.name || '',
          from_name: c.from_name || '',
          from_email: c.from_email || '',
          subject_template: c.subject_template || '',
          body_template: c.body_template || '',
          ai_personalization_enabled: c.ai_personalization_enabled || false,
        });
      } catch (err) {
        toast.error('Failed to load campaign');
      } finally {
        setFetching(false);
      }
    }
    fetchCampaign();
  }, [id, isEdit]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      if (isEdit) {
        await api.put(`/campaigns/${id}`, form);
        toast.success('Campaign updated');
        navigate(`/campaigns/${id}`);
      } else {
        const res = await api.post('/campaigns', form);
        toast.success('Campaign created');
        navigate(`/campaigns/${res.id}`);
      }
    } catch (err) {
      toast.error(isEdit ? 'Failed to update campaign' : 'Failed to create campaign');
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">
          {isEdit ? 'Edit Campaign' : 'New Campaign'}
        </h1>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Campaign Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              value={form.name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
            />
          </div>

          <div>
            <label htmlFor="from_name" className="block text-sm font-medium text-gray-700 mb-1">
              From Name
            </label>
            <input
              id="from_name"
              name="from_name"
              type="text"
              value={form.from_name}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
            />
          </div>

          <div>
            <label htmlFor="from_email" className="block text-sm font-medium text-gray-700 mb-1">
              From Email
            </label>
            <input
              id="from_email"
              name="from_email"
              type="email"
              value={form.from_email}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
            />
          </div>

          <div>
            <label htmlFor="subject_template" className="block text-sm font-medium text-gray-700 mb-1">
              Subject Template
            </label>
            <input
              id="subject_template"
              name="subject_template"
              type="text"
              value={form.subject_template}
              onChange={handleChange}
              placeholder="Hi {first_name}, ..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
            />
          </div>

          <div>
            <label htmlFor="body_template" className="block text-sm font-medium text-gray-700 mb-1">
              Body Template
            </label>
            <textarea
              id="body_template"
              name="body_template"
              rows={6}
              value={form.body_template}
              onChange={handleChange}
              placeholder={"Hello {first_name},\n\nI noticed that {company}..."}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              required
            />
            <div className="mt-2 bg-indigo-50 rounded-lg p-3">
              <p className="text-xs text-indigo-700">
                Available variables: {'{first_name}'}, {'{last_name}'}, {'{company}'}, {'{email}'}
              </p>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={form.ai_personalization_enabled}
                onClick={() =>
                  setForm((prev) => ({
                    ...prev,
                    ai_personalization_enabled: !prev.ai_personalization_enabled,
                  }))
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  form.ai_personalization_enabled
                    ? 'bg-indigo-600'
                    : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    form.ai_personalization_enabled
                      ? 'translate-x-6'
                      : 'translate-x-1'
                  }`}
                />
              </button>
              <label className="text-sm font-medium text-gray-700">
                AI Personalization
              </label>
            </div>
            <p className="text-xs text-gray-500 mt-1 ml-14">
              Use AI to personalize emails for each lead
            </p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <button
              type="button"
              onClick={() => navigate(isEdit ? `/campaigns/${id}` : '/campaigns')}
              className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loading
                ? 'Saving...'
                : isEdit
                  ? 'Update Campaign'
                  : 'Create Campaign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
