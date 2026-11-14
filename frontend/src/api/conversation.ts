const KEY = 'biblio.conversation';
export function resetConversation(): string {
  const id = crypto.randomUUID().replaceAll('-', ''); localStorage.setItem(KEY, id); return id;
}
export function getConversationId(): string {
  const id = localStorage.getItem(KEY); return id && /^[0-9a-f]{32}$/.test(id) ? id : resetConversation();
}
