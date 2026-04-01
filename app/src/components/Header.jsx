export default function Header() {
  return (
    <header className="bg-primary text-white px-6 py-4 shadow-md">
      <div className="max-w-3xl mx-auto flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-accent flex items-center justify-center font-bold text-primary text-lg">
          J
        </div>
        <div>
          <h1 className="text-lg font-semibold leading-tight">JurisIA</h1>
          <p className="text-xs text-blue-200">Assistant droit du travail français</p>
        </div>
      </div>
    </header>
  )
}
