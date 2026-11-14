import { api as defaultApi } from '../api';
import type { ApiClient } from '../api/client';
import { useAdminAuth } from './state/useAdminAuth';
import { useAdminStream } from './state/useAdminStream';
import { Login } from './screens/Login';
import { OrdersBoard } from './screens/OrdersBoard';
import { Skeleton } from '../ui/Skeleton';
function StaffWorkspace({ token, api, logout }: { token: string; api: ApiClient; logout: () => Promise<void> }) {
  const stream = useAdminStream(token, api);
  return <><header className="admin-header"><a className="brand" href="/admin.html">BIBLIO <span>Café Sách · Quầy</span></a><h1 className="screen-heading">Đơn hàng</h1><span className="connection-status"><span className={`dot ${stream.live ? 'success' : ''}`} />{stream.live ? 'Trực tuyến' : 'Đồng bộ mỗi 3 giây'}</span><button onClick={() => void stream.refetch()}>Làm mới</button><button onClick={() => void logout().catch(() => {})}>Đăng xuất</button></header><main className="admin-content"><p className="sr-only" role="status" aria-live="polite">{stream.announcement}</p>{stream.error && <p className="danger" role="alert">{stream.error}</p>}{stream.loading ? <Skeleton label="Đang tải đơn tại quầy…" /> : <OrdersBoard orders={stream.orders} onRefresh={stream.refetch} onTransition={async (id, req) => { stream.accept(await api.admin.updateStatus(id, req)); }} />}</main></>;
}
export function AdminApp({ api = defaultApi }: { api?: ApiClient }) {
  const auth = useAdminAuth(api); return auth.token ? <StaffWorkspace key={auth.token} token={auth.token} api={api} logout={auth.logout} /> : <Login onLogin={auth.login} />;
}
