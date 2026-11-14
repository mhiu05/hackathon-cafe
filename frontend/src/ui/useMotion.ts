import type { RefObject } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
gsap.registerPlugin(useGSAP);
export function useEntrance(scope: RefObject<HTMLElement | null>, dependencies: unknown[], options: { duration?: number; y?: number; scale?: number; stagger?: boolean } = {}) {
  useGSAP(() => {
    if (!scope.current || !window.matchMedia) return;
    const target = options.stagger ? [...scope.current.children] : scope.current;
    const media = gsap.matchMedia();
    media.add({ reduce: '(prefers-reduced-motion: reduce)', normal: '(prefers-reduced-motion: no-preference)' }, context => {
      if (context.conditions?.reduce) gsap.set(target, { opacity: 1, y: 0, scale: 1 });
      else gsap.fromTo(target, { opacity: .85, y: options.y ?? 6, scale: options.scale ?? 1 }, { opacity: 1, y: 0, scale: 1, duration: options.duration ?? .18, stagger: options.stagger ? .04 : 0, ease: 'power2.out', clearProps: 'transform,opacity' });
    });
    return () => media.revert();
  }, { scope, dependencies, revertOnUpdate: true });
}
