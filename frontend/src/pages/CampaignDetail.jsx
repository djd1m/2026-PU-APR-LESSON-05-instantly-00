import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import MetricCard from '../components/MetricCard';
import Modal from '../components/Modal';
import toast from 'react-hot-toast';
import {
  PaperAirplaneIcon,
  PencilSquareIcon,
  TrashIcon,
  PlusIcon,
  UsersIcon,
  EnvelopeIcon,
  EyeIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';

export default function CampaignDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState(null);
  const [steps, setSteps] = useState([]);
  const [leads, setLeads] = useState([]);
  const [emails, setEmails] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [activeTab, setActiveTab] = useState('steps');
  const [loading, setLoading] = useState(true);
  const [showAddStep, setShowAddStep] = useState(false);
  const [showAddLead, setShowAddLead] = useState(false);

  const [stepForm, setStepForm] = useState({
    step_number: 1,
    delay_days: 1,
    subject_override: '',
    body_override: '',
  });

  const [leadForm, setLeadForm] = useState({
    email: '',
    first_name: '',
    last_name: '',
    company: '',
  });

  async function fetchAll() {
    try {
      const [campaignRes, stepsRes, leadsRes, emailsRes] = await Promise.all([
        api.get(`/campaigns/${id}`),
        api.get(`/campaigns/${id}/steps`),
        api.get(`/leads?campaign_id=${id}`),
        api.get(`/emails?campaign_id=${id}`),
      ]);
      setCampaign(campaignRes);
      setSteps(stepsRes);
      setLeads(leadsRes);
      setEmails(emailsRes);

      try {
        const analyticsRes = await api.get(`/analytics/campaign/${id}`);
        setAnalytics(analyticsRes);
      } catch {
        setAnalytics(null);
      }
    } catch (err) {
      toast.error('Failed to load campaign details');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAll();
  }, [id]);

  useEffect(() => {
    if (steps.length > 0) {
      const maxStep = Math.max(...steps.map((s) => s.step_number));
      setStepForm((prev) => ({ ...prev, step_number: maxStep + 1 }));
    }
  }, [steps]);

  async function handleStatusChange(newStatus) {
    if (newStatus === 'completed' && !confirm('Complete this campaign? This cannot be undone.')) return;
    try {
      const res = await api.patch(`/campaigns/${id}/status`, {
        status: newStatus,
      });
      setCampaign(res);
      toast.success(`Campaign ${newStatus}`);
    } catch (err) {
      toast.error('Failed to update status');
    }
  }

  async function handleSendEmails() {
    try {
      await api.post(`/emails/send/${id}`, {});
      toast.success('Send job started!');
    } catch (err) {
      toast.error('Failed to start send job');
    }
  }

  async function handleDelete() {
    if (!confirm('Are you sure you want to delete this campaign?')) return;
    try {
      await api.del(`/campaigns/${id}`);
      toast.success('Campaign deleted');
      navigate('/campaigns');
    } catch (err) {
      toast.error('Failed to delete campaign');
    }
  }

  async function handleAddStep(e) {
    e.preventDefault();
    try {
      await api.post(`/campaigns/${id}/steps`, {
        step_number: Number(stepForm.step_number),
        delay_days: Number(stepForm.delay_days),
        subject_override: stepForm.subject_override || undefined,
        body_override: stepForm.body_override || undefined,
      });
      toast.success('Step added');
      setShowAddStep(false);
      setStepForm({
        step_number: steps.length + 2,
        delay_days: 1,
        subject_override: '',
        body_override: '',
      });
      const res = await api.get(`/campaigns/${id}/steps`);
      setSteps(res);
    } catch (err) {
      toast.error('Failed to add step');
    }
  }

  async function handleDeleteStep(stepId) {
    if (!confirm('Delete this step?')) return;
    try {
      await api.del(`/campaigns/${id}/steps/${stepId}`);
      toast.success('Step deleted');
      const res = await api.get(`/campaigns/${id}/steps`);
      setSteps(res);
    } catch (err) {
      toast.error('Failed to delete step');
    }
  }

  async function handleAddLead(e) {
    e.preventDefault();
    try {
      await api.post('/leads', {
        campaign_id: id,
        email: leadForm.email,
        first_name: leadForm.first_name || undefined,
        last_name: leadForm.last_name || undefined,
        company: leadForm.company || undefined,
      });
      toast.success('Lead added');
      setShowAddLead(false);
      setLeadForm({ email: '', first_name: '', last_name: '', company: '' });
      const res = await api.get(`/leads?campaign_id=${id}`);
      setLeads(res);
    } catch (err) {
      toast.error('Failed to add lead');
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="p-6">
        <div className="text-center py-12 text-gray-500">
          Campaign not found.
        </div>
      </div>
    );
  }

  const tabs = ['steps', 'leads', 'emails'];

  return (
    <div className="p-6">
      <Link
        to="/campaigns"
        className="text-sm text-indigo-600 hover:text-indigo-500 mb-2 inline-block"
      >
        &larr; Campaigns
      </Link>

      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">{campaign.name}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <div className="flex items-center gap-2">
          <Link
            to={`/campaigns/${id}/edit`}
            className="inline-flex items-center gap-1 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium"
          >
            <PencilSquareIcon className="h-4 w-4" />
            Edit
          </Link>

          {campaign.status === 'draft' && (
            <button
              onClick={() => handleStatusChange('active')}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              Activate
            </button>
          )}
          {campaign.status === 'active' && (
            <>
              <button
                onClick={() => handleStatusChange('paused')}
                className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Pause
              </button>
              <button
                onClick={() => handleStatusChange('completed')}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Complete
              </button>
            </>
          )}
          {campaign.status === 'paused' && (
            <>
              <button
                onClick={() => handleStatusChange('active')}
                className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Resume
              </button>
              <button
                onClick={() => handleStatusChange('completed')}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                Complete
              </button>
            </>
          )}

          {campaign.status === 'active' && (
            <button
              onClick={handleSendEmails}
              className="inline-flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <PaperAirplaneIcon className="h-4 w-4" />
              Send Emails
            </button>
          )}

          <button
            onClick={handleDelete}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <MetricCard
            title="Leads"
            value={analytics.total_leads}
            icon={UsersIcon}
          />
          <MetricCard
            title="Sent"
            value={analytics.total_sent}
            icon={EnvelopeIcon}
          />
          <MetricCard
            title="Opens"
            value={`${analytics.total_opens} (${analytics.open_rate.toFixed(1)}%)`}
            icon={EyeIcon}
          />
          <MetricCard
            title="Replies"
            value={`${analytics.total_replies} (${analytics.reply_rate.toFixed(1)}%)`}
            icon={ChatBubbleLeftIcon}
          />
        </div>
      )}

      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-1 text-sm font-medium capitalize transition-colors ${
                activeTab === tab
                  ? 'border-b-2 border-indigo-600 text-indigo-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'steps' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Campaign Steps
            </h3>
            <button
              onClick={() => setShowAddStep(true)}
              className="inline-flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Step
            </button>
          </div>

          {steps.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="text-center py-12 text-gray-500">
                No steps yet. Add your first step to define the email sequence.
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {steps
                .sort((a, b) => a.step_number - b.step_number)
                .map((step) => (
                  <div
                    key={step.id}
                    className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 text-sm font-bold">
                            {step.step_number}
                          </span>
                          <span className="text-sm text-gray-500">
                            Wait {step.delay_days} day
                            {step.delay_days !== 1 ? 's' : ''}
                          </span>
                        </div>
                        {step.subject_override && (
                          <div className="mt-2">
                            <span className="text-xs font-medium text-gray-500 uppercase">
                              Subject:
                            </span>
                            <p className="text-sm text-gray-900 mt-1">
                              {step.subject_override}
                            </p>
                          </div>
                        )}
                        {step.body_override && (
                          <div className="mt-2">
                            <span className="text-xs font-medium text-gray-500 uppercase">
                              Body:
                            </span>
                            <p className="text-sm text-gray-700 mt-1 whitespace-pre-wrap line-clamp-3">
                              {step.body_override}
                            </p>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleDeleteStep(step.id)}
                        className="text-red-400 hover:text-red-600 transition-colors p-1"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}

          <Modal
            isOpen={showAddStep}
            onClose={() => setShowAddStep(false)}
            title="Add Step"
          >
            <form onSubmit={handleAddStep} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Step Number
                </label>
                <input
                  type="number"
                  min="1"
                  value={stepForm.step_number}
                  onChange={(e) =>
                    setStepForm({ ...stepForm, step_number: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Delay (days)
                </label>
                <input
                  type="number"
                  min="0"
                  value={stepForm.delay_days}
                  onChange={(e) =>
                    setStepForm({ ...stepForm, delay_days: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subject Override
                </label>
                <textarea
                  rows={2}
                  value={stepForm.subject_override}
                  onChange={(e) =>
                    setStepForm({
                      ...stepForm,
                      subject_override: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  placeholder="Leave empty to use campaign subject"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Body Override
                </label>
                <textarea
                  rows={4}
                  value={stepForm.body_override}
                  onChange={(e) =>
                    setStepForm({
                      ...stepForm,
                      body_override: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  placeholder="Leave empty to use campaign body"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddStep(false)}
                  className="bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 px-4 py-2 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                >
                  Add Step
                </button>
              </div>
            </form>
          </Modal>
        </div>
      )}

      {activeTab === 'leads' && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Leads</h3>
            <button
              onClick={() => setShowAddLead(true)}
              className="inline-flex items-center gap-1 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <PlusIcon className="h-4 w-4" />
              Add Lead
            </button>
          </div>

          {leads.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="text-center py-12 text-gray-500">
                No leads yet. Add leads to start sending emails.
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
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
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {leads.map((lead) => (
                    <tr key={lead.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {lead.email}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {[lead.first_name, lead.last_name]
                          .filter(Boolean)
                          .join(' ') || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {lead.company || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <StatusBadge status={lead.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Modal
            isOpen={showAddLead}
            onClose={() => setShowAddLead(false)}
            title="Add Lead"
          >
            <form onSubmit={handleAddLead} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={leadForm.email}
                  onChange={(e) =>
                    setLeadForm({ ...leadForm, email: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  First Name
                </label>
                <input
                  type="text"
                  value={leadForm.first_name}
                  onChange={(e) =>
                    setLeadForm({ ...leadForm, first_name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Last Name
                </label>
                <input
                  type="text"
                  value={leadForm.last_name}
                  onChange={(e) =>
                    setLeadForm({ ...leadForm, last_name: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Company
                </label>
                <input
                  type="text"
                  value={leadForm.company}
                  onChange={(e) =>
                    setLeadForm({ ...leadForm, company: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddLead(false)}
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
        </div>
      )}

      {activeTab === 'emails' && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Sent Emails
          </h3>

          {emails.length === 0 ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div className="text-center py-12 text-gray-500">
                No emails sent yet.
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Subject
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Sent At
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {emails.map((email) => (
                    <tr key={email.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {email.subject}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <StatusBadge status={email.status} />
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900">
                        {email.sent_at
                          ? new Date(email.sent_at).toLocaleString()
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
