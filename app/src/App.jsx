import { useState, useRef, useEffect } from 'react'
import ChatMessage from './components/ChatMessage'
import ChatInput from './components/ChatInput'
import Header from './components/Header'

const EXAMPLE_QUESTIONS = [
  "Quel est le préavis légal en cas de licenciement ?",
  "Quels sont les droits du salarié en cas de harcèlement moral ?",
  "Combien de jours de congés payés par an ?",
  "Quelles sont les conditions d'un licenciement pour faute grave ?",
]

export default function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendQuestion = async (question) => {
    if (!question.trim() || loading) return

    const userMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      const apiBase = import.meta.env.VITE_API_URL ?? ''
      const res = await fetch(`${apiBase}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (!res.ok) throw new Error(`Erreur ${res.status}`)

      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.answer, sources: data.sources },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: "Une erreur est survenue. Vérifiez que l'API est bien démarrée sur le port 8000.",
          sources: [],
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <Header />

      <main className="flex-1 overflow-y-auto px-4 py-6 max-w-3xl mx-auto w-full">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-8 text-center">
            <div>
              <h2 className="text-2xl font-semibold text-primary mb-2">
                Posez votre question juridique
              </h2>
              <p className="text-gray-500 text-sm">
                JurisIA répond en se basant exclusivement sur le Code du travail français.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendQuestion(q)}
                  className="text-left p-3 rounded-xl border border-gray-200 bg-white hover:border-accent hover:shadow-sm transition text-sm text-gray-700"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {messages.map((msg, i) => (
              <ChatMessage key={i} message={msg} />
            ))}
            {loading && (
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold shrink-0">
                  J
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 flex gap-1 items-center">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      <div className="border-t bg-white px-4 py-4 max-w-3xl mx-auto w-full">
        <ChatInput onSend={sendQuestion} disabled={loading} />
        <p className="text-center text-xs text-gray-400 mt-2">
          JurisIA informe sur le droit — ne remplace pas un conseil juridique personnalisé.
        </p>
      </div>
    </div>
  )
}
