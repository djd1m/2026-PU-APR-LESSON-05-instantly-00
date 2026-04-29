import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  MegaphoneIcon,
  UsersIcon,
  ServerIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuthStore } from '../store/auth';

const navItems = [
  { label: 'Dashboard', icon: HomeIcon, to: '/' },
  { label: 'Campaigns', icon: MegaphoneIcon, to: '/campaigns' },
  { label: 'Leads', icon: UsersIcon, to: '/leads' },
  { label: 'Email Accounts', icon: ServerIcon, to: '/accounts' },
  { label: 'Analytics', icon: ChartBarIcon, to: '/analytics' },
  { label: 'Settings', icon: Cog6ToothIcon, to: '/settings' },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);

  const handleLogout = () => {
    useAuthStore.getState().logout();
    navigate('/login');
  };

  return (
    <div className="bg-slate-900 w-64 flex flex-col h-full">
      <div className="py-6 px-6">
        <span className="text-white text-xl font-bold">Instantly.ai</span>
      </div>

      <nav className="flex-1">
        {navItems.map((item) => {
          const isActive =
            item.to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.to);

          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg mx-3 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto border-t border-slate-700 p-4">
        {user && (
          <p className="text-sm text-slate-300 truncate mb-3">{user.email}</p>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-sm transition-colors"
        >
          <ArrowRightOnRectangleIcon className="w-5 h-5" />
          Logout
        </button>
      </div>
    </div>
  );
}
