import { describe, expect, it } from 'vitest';
import { parseSseText, readSse } from './sse';
import transcript from '../../../contracts/fixtures/agent_stream.sse?raw';

describe('SSE wire contract', () => {
  it('parses all 35 fixture events without treating comments as messages', () => {
    const events = parseSseText(transcript);
    expect(events).toHaveLength(35);
    expect(events[0].event).toBe('run_started');
    expect(events.filter(e => e.event === 'order_draft')).toHaveLength(1);
  });
  it('handles split lines, UTF-8 bytes, CRLF and comments without duplication', async () => {
    const bytes = new TextEncoder().encode(': ping\r\n\r\nevent: text_delta\r\ndata: {"delta":"Xin chào"}\r\n\r\nevent: done\ndata: {}\n\n');
    const body = new ReadableStream({ start(c) { for (const byte of bytes) c.enqueue(new Uint8Array([byte])); c.close(); } });
    const got: [string, unknown][] = [];
    await readSse(new Response(body), (n, d) => got.push([n, d]));
    expect(got).toEqual([['text_delta', { delta: 'Xin chào' }], ['done', {}]]);
  });
  it('joins multiline data and ignores an incomplete final frame', () => {
    expect(parseSseText('event: message\ndata: {"a":\ndata: 1}\n\nevent: lost\ndata: {}')).toEqual([{ event: 'message', data: { a: 1 } }]);
  });
});
