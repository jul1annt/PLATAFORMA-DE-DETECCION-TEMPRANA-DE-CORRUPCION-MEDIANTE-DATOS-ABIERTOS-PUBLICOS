import Dashboard from './pages/Dashboard'

function App() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xl">A</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Plataforma Anticorrupción
            </h1>
          </div>
          <div className="text-sm text-gray-500 font-medium px-3 py-1 bg-gray-100 rounded-full">
            Admin Panel v1.0
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <Dashboard />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-gray-500">
          Epic 1: Ingesta de Datos &copy; {new Date().getFullYear()}
        </div>
      </footer>
    </div>
  )
}

export default App
