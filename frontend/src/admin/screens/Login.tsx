import { useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import { Button } from '../../ui/Button';
export function Login({ onLogin }: { onLogin: (pin: string) => Promise<void> }) {
  const [pin, setPin] = useState(''), [error, setError] = useState(''), [pending, setPending] = useState(false); const lock = useRef(false);
  return <main className="login-screen"><p className="brand">BIBLIO <span>Café Sách · Quầy</span></p><h1 className="screen-heading">Chào bạn, vào ca thôi.</h1><p className="muted">Nhập mã PIN của quán để quản lý đơn.</p><form onSubmit={async e => { e.preventDefault(); if (lock.current) return; lock.current = true; setPending(true); setError(''); try { await onLogin(pin); } catch (e) { setError(e instanceof ApiError && e.status === 401 ? 'Mã PIN không đúng' : e instanceof ApiError && e.status === 429 ? 'Thử lại sau 1 phút' : e instanceof Error ? e.message : 'Không đăng nhập được'); } finally { lock.current = false; setPending(false); } }}>
    <label htmlFor="admin-pin">Mã PIN</label><input id="admin-pin" type="password" autoComplete="current-password" value={pin} maxLength={128} onChange={e => setPin(e.target.value)} aria-describedby={error ? 'login-error' : undefined} aria-invalid={!!error} required disabled={pending} />{error && <p className="danger" id="login-error" role="alert">{error}</p>}<Button disabled={pending || !pin.trim()} aria-busy={pending}>Đăng nhập</Button></form><a href="/">Về trang khách</a></main>;
}
