import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Sparkles, Send, Bot, User, Cloud, HardDrive } from 'lucide-react'
import { askAssistant } from '@/lib/api'

/**
 * Чат с AI-Технологом на экране "Обзор" (Фаза 17, часть 5, по прямому
 * запросу пользователя) — заменяет карточки "Состояние backend"/"Текущая
 * деталь". Отвечает по реальному содержимому БД НСИ (keyword-поиск в
 * AssistantService, см. backend), не по общим знаниям модели — источник
 * ответа (LLM/шаблон) всегда показывается явно под сообщением, тот же
 * принцип прозрачности, что и в резюме отчёта КД.
 */

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  generatedBy?: 'llm' | 'template'
}

const SUGGESTED_QUESTIONS = [
  'Какие марки стали есть в базе?',
  'Что за станок 16К20?',
  'Какой материал подходит для пропеллера дрона?',
]

export function AssistantChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  const mutation = useMutation({
    mutationFn: (question: string) => askAssistant(question),
    onSuccess: (reply) => {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', text: reply.text, generatedBy: reply.generated_by },
      ])
    },
    onError: (error: Error) => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          text: `Не удалось получить ответ: ${error.message}`,
        },
      ])
    },
  })

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, mutation.isPending])

  function send(question: string) {
    const trimmed = question.trim()
    if (!trimmed || mutation.isPending) return
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', text: trimmed }])
    setInput('')
    mutation.mutate(trimmed)
  }

  return (
    <div className="flex h-full flex-col rounded-2xl border border-border bg-surface">
      <div className="flex items-center gap-2 border-b border-border px-5 py-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/10 text-brand">
          <Sparkles className="h-4 w-4" />
        </span>
        <div>
          <div className="text-sm font-semibold text-ink">AI-Технолог</div>
          <div className="text-[11px] text-ink-dim">Вопросы по НСИ и технологичности — ответ по базе данных</div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div>
            <p className="text-sm text-ink-dim">
              Спросите про материалы, оборудование, оснастку или классы деталей БПЛА — ответ строится
              только на найденных в локальной базе НСИ фактах.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="rounded-full border border-border px-3 py-1.5 text-xs text-ink-dim transition-colors hover:border-brand hover:text-brand"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <div key={m.id} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                m.role === 'user' ? 'bg-brand/10 text-brand' : 'bg-muted text-ink-dim'
              }`}
            >
              {m.role === 'user' ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
            </span>
            <div className={`max-w-[85%] ${m.role === 'user' ? 'text-right' : ''}`}>
              <div
                className={`whitespace-pre-line rounded-2xl px-3.5 py-2.5 text-sm ${
                  m.role === 'user' ? 'bg-brand text-white' : 'bg-muted text-ink'
                }`}
              >
                {m.text}
              </div>
              {m.generatedBy && (
                <div className="mt-1 flex items-center gap-1 text-[10px] text-ink-dim">
                  {m.generatedBy === 'llm' ? (
                    <>
                      <Cloud className="h-3 w-3" /> YandexGPT по фактам из НСИ
                    </>
                  ) : (
                    <>
                      <HardDrive className="h-3 w-3" /> офлайн-шаблон по фактам из НСИ
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {mutation.isPending && (
          <div className="flex items-center gap-2 text-xs text-ink-dim">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted">
              <Bot className="h-3.5 w-3.5" />
            </span>
            Поиск по базе НСИ…
          </div>
        )}
      </div>

      <form
        className="flex items-center gap-2 border-t border-border p-3"
        onSubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Спросите про материал, станок, оснастку…"
          className="flex-1 rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-brand"
        />
        <button
          type="submit"
          disabled={!input.trim() || mutation.isPending}
          aria-label="Отправить"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand text-white transition-opacity disabled:opacity-40"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  )
}
