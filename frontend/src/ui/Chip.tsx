import type { ButtonHTMLAttributes } from 'react';
export function Chip({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) { return <button className={`chip ${className}`} {...props} />; }
