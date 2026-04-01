import { useState } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Posez votre question juridique..."
        rows={1}
        disabled={disabled}
        className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50 leading-relaxed"
        style={{ maxHeight: '120px', overflowY: 'auto' }}
        onInput={(e) => {
          e.target.style.height = 'auto'
          e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`
        }}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="bg-primary text-white rounded-xl px-5 py-3 text-sm font-medium hover:bg-blue-900 disabled:opacity-40 disabled:cursor-not-allowed transition shrink-0"
      >
        Envoyer
      </button>
    </form>
  )
}
