import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import AssessDevice from './pages/AssessDevice';
import AssetInventory from './pages/AssetInventory';
import ApprovalQueue from './pages/ApprovalQueue';
import AuditTrail from './pages/AuditTrail';
import AIAssistant from './pages/AIAssistant';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="assess" element={<AssessDevice />} />
        <Route path="inventory" element={<AssetInventory />} />
        <Route path="approvals" element={<ApprovalQueue />} />
        <Route path="audit" element={<AuditTrail />} />
        <Route path="ai" element={<AIAssistant />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
