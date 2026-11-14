import { useRef, type ReactNode } from 'react';
import { useEntrance } from '../../ui/useMotion';
export function OrderTile({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLElement>(null); useEntrance(ref, [], { duration: 1.2, y: 0, scale: 1.01 });
  return <article ref={ref} className="admin-slip">{children}</article>;
}
