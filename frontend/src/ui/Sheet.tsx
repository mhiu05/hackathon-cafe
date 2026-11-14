import { useEffect, useId, useRef, type ReactNode } from 'react';
export function Sheet({ title, children, onClose }: { title: string; children: ReactNode; onClose?: () => void }) {
  const ref = useRef<HTMLDialogElement>(null); const label = useId(); const close = useRef(onClose); close.current = onClose;
  useEffect(() => { const dialog = ref.current!; const previous = document.activeElement as HTMLElement | null;
    if (dialog.showModal) dialog.showModal(); else dialog.setAttribute('open', '');
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') { e.preventDefault(); close.current?.(); } };
    dialog.addEventListener('keydown', onKey);
    return () => { dialog.removeEventListener('keydown', onKey); dialog.close?.(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className="sheet" aria-labelledby={label} onCancel={e => { e.preventDefault(); onClose?.(); }} onClick={e => { if (e.target === e.currentTarget) onClose?.(); }}>
    <div className="sheet-body"><div className="section-heading"><h2 id={label}>{title}</h2>{onClose && <button onClick={onClose}>Đóng</button>}</div>{children}</div>
  </dialog>;
}
