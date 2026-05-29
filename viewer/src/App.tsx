import { useState } from 'react';
import { Wallet, LogOut, Shield } from 'lucide-react';
import { FileUpload } from '@/components/FileUpload';
import { SubscriptionsTable } from '@/components/SubscriptionsTable';
import { OverspendingAnalysis } from '@/components/OverspendingAnalysis';

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleLogout = () => {
    setSessionId(null);
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans text-gray-900 selection:bg-blue-100">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-blue-600 p-2 rounded-lg">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
                ExpenseEye
              </h1>
              <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold -mt-1">Analytics Viewer</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com/shan3520/expenseeye"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="GitHub Repository"
              aria-label="GitHub Repository"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>
            </a>

            {sessionId && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-red-600 transition-colors px-3 py-1.5 rounded-md hover:bg-red-50"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">End Session</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-12">
        {!sessionId ? (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500 py-12">
            <div className="text-center max-w-2xl mx-auto mb-10">
              <h2 className="text-3xl font-extrabold tracking-tight text-gray-900 sm:text-4xl">
                Understand your spending.<br/>
                <span className="text-blue-600">Keep your data private.</span>
              </h2>
              <p className="mt-4 text-lg text-gray-500">
                Upload your bank statement to instantly detect recurring subscriptions and analyze overspending patterns.
              </p>
              <div className="mt-6 flex items-center justify-center gap-2 text-sm text-gray-500 bg-white inline-flex px-4 py-2 rounded-full border border-gray-200 shadow-sm">
                <Shield className="w-4 h-4 text-green-500" />
                All processing happens locally. No data is stored or shared.
              </div>
            </div>
            <FileUpload onUploadSuccess={setSessionId} />
          </section>
        ) : (
          <div className="space-y-12 animate-in fade-in duration-500">
            <section className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-200 bg-gray-50/50">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span className="p-1 bg-blue-100 text-blue-600 rounded">📅</span>
                  Recurring Subscriptions
                </h3>
              </div>
              <div className="p-6">
                <SubscriptionsTable sessionId={sessionId} />
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="px-6 py-5 border-b border-gray-200 bg-gray-50/50">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <span className="p-1 bg-indigo-100 text-indigo-600 rounded">📊</span>
                  Overspending Analysis
                </h3>
              </div>
              <div className="p-6">
                <OverspendingAnalysis sessionId={sessionId} />
              </div>
            </section>
          </div>
        )}
      </main>

      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-gray-500">
            &copy; {new Date().getFullYear()} ExpenseEye Analytics. Privacy-first by design.
          </p>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <span>Powered by React & Tailwind CSS</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
