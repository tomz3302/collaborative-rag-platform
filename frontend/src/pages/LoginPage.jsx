import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Box, LogIn, Loader2, AlertCircle } from 'lucide-react';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      if (err.message === 'LOGIN_BAD_CREDENTIALS') {
        setError('Invalid email or password');
      } else if (err.message === 'LOGIN_USER_NOT_VERIFIED') {
        setError('Please verify your email before logging in');
      } else {
        setError(err.message || 'Unable to connect to server');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-black font-mono flex flex-col items-center justify-center p-8">
      
      {/* HEADER */}
      <div className="mb-12 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-black text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <Box size={32} />
        </div>
        <h1 className="text-4xl font-black tracking-tighter">Clark</h1>
        <p className="opacity-60 text-sm">AUTHENTICATE_TO_ACCESS_SYSTEM</p>
      </div>

      {/* LOGIN CARD */}
      <div className="w-full max-w-md bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8">
        <div className="flex items-center gap-3 mb-6 border-b-2 border-black pb-4">
          <LogIn size={20} />
          <h2 className="font-bold text-lg uppercase tracking-wider">System_Login</h2>
        </div>

        {/* ERROR ALERT */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border-2 border-red-500 flex items-center gap-3">
            <AlertCircle size={20} className="text-red-500 flex-shrink-0" />
            <span className="text-sm text-red-700 font-medium">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase mb-2">Email_Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border-2 border-black p-3 bg-gray-50 focus:bg-white focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all font-mono"
              placeholder="22p0521@eng.asu.edu.eg"
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase mb-2">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border-2 border-black p-3 bg-gray-50 focus:bg-white focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all font-mono"
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-black text-white font-bold border-2 border-black hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 mt-6"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                AUTHENTICATING...
              </>
            ) : (
              'LOG IN'
            )}
          </button>
        </form>

        {/* REGISTER LINK */}
        <div className="mt-6 pt-6 border-t-2 border-gray-200 text-center">
          <p className="text-sm opacity-60">
            No account?{' '}
            <Link 
              to="/register" 
              className="font-bold text-black underline underline-offset-4 hover:opacity-70 transition-opacity"
            >
              Register_Here
            </Link>
          </p>
        </div>
      </div>

      {/* FOOTER */}
      <p className="mt-8 text-xs opacity-40">
        &copy; 2025 Clark. No rights reserved.
      </p>
    </div>
  );
};

export default LoginPage;