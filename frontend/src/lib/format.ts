export function formatVnd(n: number): string { return `${new Intl.NumberFormat('vi-VN').format(n)}đ`; }
export function formatTime(iso: string): string { return new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Bangkok', hour: '2-digit', minute: '2-digit' }).format(new Date(iso)); }
export function formatDate(iso: string): string { return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Bangkok' }).format(new Date(iso)); }
