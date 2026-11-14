export function Skeleton({ label = 'Đang tải…' }: { label?: string }) { return <div className="skeleton" role="status"><p>{label}</p><div /><div /><div /></div>; }
