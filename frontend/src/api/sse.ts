type SseEvent = { event: string; data: unknown };
function frame(text: string): SseEvent | null {
  let event = 'message'; const data: string[] = [];
  for (const line of text.split(/\r\n|\r|\n/)) {
    if (line.startsWith(':')) continue;
    const colon = line.indexOf(':');
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? '' : line.slice(colon + 1).replace(/^ /, '');
    if (field === 'event') event = value;
    if (field === 'data') data.push(value);
  }
  return data.length ? { event, data: JSON.parse(data.join('\n')) as unknown } : null;
}
function parser(onEvent: (event: SseEvent) => void) {
  let buffer = '';
  return (part: string) => {
    buffer += part;
    let separator: RegExpExecArray | null;
    while ((separator = /\r\n\r\n|\n\n|\r\r/.exec(buffer))) {
      const message = frame(buffer.slice(0, separator.index));
      buffer = buffer.slice(separator.index + separator[0].length);
      if (message) onEvent(message);
    }
  };
}
export function parseSseText(text: string): SseEvent[] {
  const events: SseEvent[] = []; parser(e => events.push(e))(text); return events;
}
export async function readSse(response: Response, onEvent: (name: string, data: unknown) => void): Promise<void> {
  if (!response.body) throw new Error('Máy chủ không trả về luồng dữ liệu.');
  const reader = response.body.getReader(); const decoder = new TextDecoder();
  const push = parser(e => onEvent(e.event, e.data));
  try {
    while (true) { const { done, value } = await reader.read(); if (done) break; push(decoder.decode(value, { stream: true })); }
    push(decoder.decode());
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
