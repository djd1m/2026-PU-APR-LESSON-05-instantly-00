import { useState, useEffect } from 'react';
import { api } from '../api/client';
import MetricCard from '../components/MetricCard';
import {
  UsersIcon,
  EnvelopeIcon,
  EyeIcon,
  ChatBubbleLeftIcon,
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import toast from 'react-hot-toast';

export default function Analytics() {
  const [campaigns, setCampaigns] = useState([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState('');
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const data = await api.get('/campaigns');
        setCampaigns(data);
      } catch (err) {
        toast.error(err.detail || 'Failed to load campaigns');
      }
    };
    fetchCampaigns();
  }, []);

  useEffect(() => {
    if (!selectedCampaignId) {
      setStats(null);
      return;
    }
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await api.get(`/analytics/campaign/${selectedCampaignId}`);
        setStats(data);
      } catch (err) {
        toast.error(err.detail || 'Failed to load analytics');
        setStats(null);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [selectedCampaignId]);

  const chartData = stats
    ? [
        { name: 'Opens', value: stats.total_opens, fill: '#6366f1' },
        { name: 'Clicks', value: stats.total_clicks, fill: '#8b5cf6' },
        { name: 'Replies', value: stats.total_replies, fill: '#10b981' },
        { name: 'Bounces', value: stats.total_bounces, fill: '#ef4444' },
      ]
    : [];

  const funnelData = stats
    ? [
        {
          label: 'Sent',
          count: stats.total_sent,
          percent: 100,
          color: 'bg-indigo-600',
        },
        {
          label: 'Opened',
          count: stats.total_opens,
          percent: stats.open_rate || 0,
          color: 'bg-violet-500',
        },
        {
          label: 'Clicked',
          count: stats.total_clicks,
          percent: stats.click_rate || 0,
          color: 'bg-purple-500',
        },
        {
          label: 'Replied',
          count: stats.total_replies,
          percent: stats.reply_rate || 0,
          color: 'bg-emerald-500',
        },
      ]
    : [];

  const formatRate = (rate) => {
    if (rate == null) return '0.0%';
    return `${Number(rate).toFixed(1)}%`;
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
      </div>

      <div className="mb-6">
        <select
          value={selectedCampaignId}
          onChange={(e) => setSelectedCampaignId(e.target.value)}
          className="bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
        >
          <option value="">Select a campaign...</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      {!selectedCampaignId && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center text-gray-500">
          Select a campaign to view analytics
        </div>
      )}

      {selectedCampaignId && loading && (
        <div className="text-center text-gray-500 py-12">Loading analytics...</div>
      )}

      {selectedCampaignId && !loading && stats && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <MetricCard
              title="Total Leads"
              value={stats.total_leads}
              icon={UsersIcon}
            />
            <MetricCard
              title="Emails Sent"
              value={stats.total_sent}
              icon={EnvelopeIcon}
            />
            <MetricCard
              title="Open Rate"
              value={formatRate(stats.open_rate)}
              icon={EyeIcon}
            />
            <MetricCard
              title="Reply Rate"
              value={formatRate(stats.reply_rate)}
              icon={ChatBubbleLeftIcon}
            />
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Campaign Performance</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={index} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mt-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Conversion Funnel</h2>
            <div className="space-y-4">
              {funnelData.map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="font-medium text-gray-700">{item.label}</span>
                    <span className="text-gray-500">
                      {item.count} ({item.percent.toFixed(1)}%)
                    </span>
                  </div>
                  <div className="h-8 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color} rounded-full transition-all`}
                      style={{ width: `${Math.max(item.percent, 2)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-6 mt-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <p className="text-3xl font-bold text-indigo-600">
                {formatRate(stats.open_rate)}
              </p>
              <p className="text-sm text-gray-500 mt-1">Open Rate</p>
              <p className="text-xs text-gray-400">of sent emails</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <p className="text-3xl font-bold text-indigo-600">
                {formatRate(stats.click_rate)}
              </p>
              <p className="text-sm text-gray-500 mt-1">Click Rate</p>
              <p className="text-xs text-gray-400">of sent emails</p>
            </div>
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <p className="text-3xl font-bold text-indigo-600">
                {formatRate(stats.reply_rate)}
              </p>
              <p className="text-sm text-gray-500 mt-1">Reply Rate</p>
              <p className="text-xs text-gray-400">of sent emails</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
