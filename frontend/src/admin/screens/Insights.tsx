import { useEffect, useState } from 'react';
import type { AdminInsights, OrderStatus } from '../../api/types';
import { getAdminInsights } from '../../api/insights';
import { formatVnd } from '../../lib/format';
import { Skeleton } from '../../ui/Skeleton';
const STATUS: Record<OrderStatus, string> = { pending: 'Chờ xác nhận', confirmed: 'Đã nhận', preparing: 'Đang pha', ready: 'Sẵn sàng', completed: 'Hoàn tất', rejected: 'Từ chối', cancelled: 'Đã hủy' };
export function Insights({ load = getAdminInsights }: { load?: () => Promise<AdminInsights> }) {
  const [data, setData] = useState<AdminInsights | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; void load().then(d => { if (active) { setData(d); setError(''); } }).catch(e => { if (active) setError(e instanceof Error ? e.message : 'Chưa tải được tổng quan'); }); return () => { active = false; }; }, [load, retry]);
  if (error) return <section><h1 className="screen-heading">Tổng quan</h1><p role="alert" className="danger">{error}</p><button onClick={() => { setError(''); setRetry(r => r + 1); }}>Thử lại</button></section>;
  if (!data) return <Skeleton label="Đang đọc tổng quan từ quán…" />;
  return <section className="insights-screen"><div className="section-heading"><h1 className="screen-heading">Tổng quan</h1><button onClick={() => setRetry(r => r + 1)}>Làm mới tổng quan</button></div><p className="muted">Số liệu máy chủ tại lần tải gần nhất.</p><dl className="insights-summary"><div><dt>Tổng đơn</dt><dd>{data.orders_total}</dd></div><div><dt>Doanh thu đơn hoàn tất</dt><dd className="price">{formatVnd(data.revenue_completed_vnd)}</dd></div></dl>
    <table><caption>Đơn theo trạng thái</caption><thead><tr><th scope="col">Trạng thái</th><th scope="col">Số đơn</th></tr></thead><tbody>{Object.entries(data.orders_by_status).map(([s, count]) => <tr key={s}><th scope="row">{STATUS[s as OrderStatus]}</th><td>{count}</td></tr>)}</tbody></table>
    <table><caption>Món được đặt nhiều</caption><thead><tr><th scope="col">Tên món</th><th scope="col">Số lượng</th></tr></thead><tbody>{data.top_items.map(item => <tr key={item.item_id}><th scope="row">{item.name}</th><td>{item.quantity}</td></tr>)}{!data.top_items.length && <tr><td colSpan={2}>Chưa có món được đặt</td></tr>}</tbody></table>
    <table><caption>Hoạt động trợ lý</caption><tbody><tr><th scope="row">Lượt chạy</th><td>{data.agent.runs}</td></tr><tr><th scope="row">Token đầu vào</th><td>{data.agent.input_tokens}</td></tr><tr><th scope="row">Token đầu ra</th><td>{data.agent.output_tokens}</td></tr><tr><th scope="row">Lỗi công cụ</th><td>{data.agent.tool_errors}</td></tr>{Object.entries(data.agent.tool_calls).map(([tool, count]) => <tr key={tool}><th scope="row">{tool}</th><td>{count}</td></tr>)}</tbody></table>
  </section>;
}
