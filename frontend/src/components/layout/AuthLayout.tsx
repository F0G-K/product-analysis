import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary-600 text-white text-xl font-bold mb-3">
            <svg className="w-7 h-7" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 3a1 1 0 011-1h4l3 6-2 4h2l-2 4H4l3-6-2-4H4V3z" clipRule="evenodd" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-gray-800">产品管理智能助手</h1>
          <p className="text-sm text-gray-400 mt-1">AI 驱动的产品管理平台</p>
        </div>

        {/* Content card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
