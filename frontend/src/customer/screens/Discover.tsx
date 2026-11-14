import type { CafeProfile } from '../../api/types';
import { formatDate } from '../../lib/format';
import { Button } from '../../ui/Button';
import { useRef } from 'react';
import { useEntrance } from '../../ui/useMotion';
export function Discover({ cafe, onMenu, onChat }: { cafe: CafeProfile; onMenu: () => void; onChat: () => void }) {
  const masthead = useRef<HTMLElement>(null); useEntrance(masthead, [], { stagger: true });
  return <><section ref={masthead} className="masthead"><div className="masthead-wordmark">{cafe.brand_name.toUpperCase()}<span>Café Sách</span></div><div className="masthead-rule" /><p>{cafe.address}</p><p className="open-status"><span className={`dot ${cafe.is_open_now ? 'success' : ''}`} />{cafe.is_open_now ? 'Đang mở' : 'Đang đóng'} · {cafe.opening_hours.open}–{cafe.opening_hours.close}</p><p><a href={`tel:${cafe.phone.replaceAll(' ', '')}`}>{cafe.phone}</a></p><div className="actions"><Button onClick={onChat}>Hỏi Biblio</Button><button onClick={onMenu}>Xem menu</button></div></section>
    <section className="content-section"><h1 className="screen-heading">Một khoảng yên, một trang mới.</h1><p className="muted">Khám phá không gian, chọn món và hỏi Biblio về quán.</p><div className="highlights">{cafe.highlights.map((h, n) => { const source = cafe.sources.find(s => s.source_id === h.source_id); return <article className="index-card" key={`${h.source_id}-${n}`}><h2>{h.label}</h2>{source && <small className="source-stamp">{source.url ? <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a> : source.title}<br />{formatDate(source.retrieved_at)}</small>}</article>; })}</div>
    {cafe.rating_snapshot && <p className="rating"><strong>{cafe.rating_snapshot.rating.toLocaleString('vi-VN')}/5</strong> · {cafe.rating_snapshot.reviews_count} đánh giá · {formatDate(cafe.rating_snapshot.as_of)}</p>}
    <p>{cafe.wifi.available ? 'Có Wi-Fi' : 'Chưa có thông tin Wi-Fi'} · Mật khẩu: hỏi nhân viên.</p><a href={cafe.channels.google_maps_url} target="_blank" rel="noreferrer">Chỉ đường đến quán</a><p className="data-notice">{cafe.data_notice}</p></section></>;
}
