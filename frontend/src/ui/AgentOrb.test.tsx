import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import type { ThinkingOrbProps } from 'thinking-orbs';
import { AgentOrb } from './AgentOrb';
vi.mock('thinking-orbs', () => ({ ThinkingOrb: (p: ThinkingOrbProps) => <div data-testid="orb" data-state={p.state} data-paused={p.paused} /> }));
it('maps real backend state to orb state and Vietnamese accessible label', () => {
  const { rerender } = render(<AgentOrb state="searching" />);
  expect(screen.getByTestId('orb')).toHaveAttribute('data-state', 'searching');
  expect(screen.getByRole('img', { name: 'Đang tra cứu' })).toBeInTheDocument();
  rerender(<AgentOrb state="working" />); expect(screen.getByTestId('orb')).toHaveAttribute('data-state', 'working');
  rerender(<AgentOrb state="error" />); expect(screen.getByTestId('orb')).toHaveAttribute('data-paused', 'true');
});
