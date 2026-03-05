import { useState, useRef, useEffect } from 'react';
import { chat } from '../services/api';
import { Send, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const SUGGESTIONS = [
  'Which assets should be prioritised for recycling first?',
  'What is the current fleet health summary?',
  'How can I reduce e-waste generated this quarter?',
  'Explain the risk scoring methodology.',
];

/** Splits LLM response into main body + clickable follow-up chips */
function MessageContent({ content, onSend }: { content: string; onSend: (q: string) => void }) {
  const idx = content.search(/suggested follow[- ]?up (queries|questions):?/i);
  if (idx === -1) {
    return <span className="whitespace-pre-wrap">{content}</span>;
  }
  const mainBody = content.slice(0, idx).trim();
  const remainder = content.slice(idx).replace(/suggested follow[- ]?up (queries|questions):?\s*/i, '');
  const followUps = remainder
    .split('\n')
    .map(l => l.replace(/^[\s\-•*\d.]+/, '').trim())
    .filter(l => l.length > 5);
  return (
    <div>
      <span className="whitespace-pre-wrap">{mainBody}</span>
      {followUps.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-gray-100">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-400 mb-2">Follow-up suggestions</p>
          <div className="flex flex-col gap-1.5">
            {followUps.map((q, i) => (
              <button key={i} onClick={() => onSend(q)}
                className="text-xs text-left px-2.5 py-1.5 rounded-lg bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 transition-colors">
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([{
    role: 'assistant',
    content: 'Hello! I\'m your AI Fleet Assistant. Ask me anything about your device fleet, risk assessments, or lifecycle recommendations.',
  }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async (text?: string) => {
    const query = text ?? input;
    if (!query.trim() || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: query }]);
    setLoading(true);
    try {
      const res = await chat(query);
      setMessages(prev => [...prev, { role: 'assistant', content: res.response }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-6 pb-0">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-gray-900">AI Assistant</h1>
        <p className="text-sm text-gray-500 mt-0.5">Powered by Amazon Bedrock · Qwen3 80B</p>
      </div>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 mb-4">
        {SUGGESTIONS.map(s => (
          <button key={s} onClick={() => send(s)}
            className="text-xs px-3 py-1.5 bg-green-50 text-green-700 rounded-full border border-green-200 hover:bg-green-100 transition-colors">
            {s}
          </button>
        ))}
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role === 'assistant' && (
              <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
                <Bot size={16} className="text-green-600" />
              </div>
            )}
            <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-green-600 text-white rounded-br-sm'
                : 'bg-white border border-gray-100 text-gray-700 rounded-bl-sm shadow-sm'
            }`}>
              {m.role === 'assistant'
                ? <MessageContent content={m.content} onSend={send} />
                : m.content
              }
            </div>
            {m.role === 'user' && (
              <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center shrink-0">
                <User size={16} className="text-gray-600" />
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center shrink-0">
              <Bot size={16} className="text-green-600" />
            </div>
            <div className="bg-white border border-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                {[0, 1, 2].map(i => (
                  <div key={i} className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="bg-white border-t border-gray-100 py-4 flex gap-3">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about your fleet…"
          className="flex-1 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        />
        <button onClick={() => send()} disabled={loading || !input.trim()}
          className="bg-green-600 hover:bg-green-700 text-white rounded-xl px-4 py-2.5 transition-colors disabled:opacity-50">
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
