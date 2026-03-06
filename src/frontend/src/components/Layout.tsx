import { Outlet, NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ScanLine,
  Package,
  CheckSquare,
  ScrollText,
  MessageSquare,
  Settings,
  Leaf,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/dashboard',  icon: LayoutDashboard, label: 'Dashboard'       },
  { to: '/assess',     icon: ScanLine,        label: 'Assess Device'   },
  { to: '/inventory',  icon: Package,         label: 'Asset Inventory' },
  { to: '/approvals',  icon: CheckSquare,     label: 'Approval Queue'  },
  { to: '/audit',      icon: ScrollText,      label: 'Audit Trail'     },
  { to: '/ai',         icon: MessageSquare,   label: 'AI Assistant'    },
  { to: '/settings',   icon: Settings,        label: 'Settings'        },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50 text-gray-900">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="px-6 py-5 border-b border-gray-700 flex items-center gap-3">
          <Leaf className="text-green-400" size={24} />
          <div>
            <p className="font-bold text-base leading-tight">Capital-E</p>
            <p className="text-xs text-gray-400">E-Waste/E-Scrap Expert</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-green-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-gray-700 text-xs text-gray-400">
          <p>© 2026 HPE Singularity Crew. All rights reserved.</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
