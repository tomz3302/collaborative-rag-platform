import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Box, UserPlus, Loader2, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

const RegisterPage = () => {
    
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [emailWarning, setEmailWarning] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const { register } = useAuth();
  const navigate = useNavigate();

  // Validate email domain
  const validateEmail = (emailValue) => {
    if (emailValue && !emailValue.endsWith('@eng.asu.edu.eg')) {
      setEmailWarning('Only @eng.asu.edu.eg emails are allowed');
      return false;
    }
    setEmailWarning('');
    return true;
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    if (value) validateEmail(value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate email domain
    if (!validateEmail(email)) {
      setError('Only @eng.asu.edu.eg email addresses are allowed');
      return;
    }

    // Check password match
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Check password length
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      await register(email, password, fullName);
      setSuccess(true);
      
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate('/login');
      }, 3000);
    } catch (err) {
      if (err.message === 'REGISTER_USER_ALREADY_EXISTS') {
        setError('An account with this email already exists');
      } else if (err.message === 'REGISTER_INVALID_PASSWORD') {
        setError('Password does not meet requirements');
      } else {
        setError(err.message || 'Registration failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 text-black font-mono flex flex-col items-center justify-center p-8">
        <div className="w-full max-w-md bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-500 text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-6">
            <CheckCircle size={32} />
          </div>
          <h2 className="text-2xl font-bold mb-4">REGISTRATION_COMPLETE</h2>
          <p className="opacity-60 mb-4">
            A verification email has been sent to <span className="font-bold">{email}</span>
          </p>
          <p className="text-sm opacity-40">
            Redirecting to login...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 text-black font-mono flex flex-col items-center justify-center p-8">
      
      {/* HEADER */}
      <div className="mb-12 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-black text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <Box size={32} />
        </div>
        <h1 className="text-4xl font-black tracking-tighter">Clark</h1>
        <p className="opacity-60 text-sm">CREATE_NEW_USER_ACCOUNT</p>
      </div>

      {/* REGISTER CARD */}
      <div className="w-full max-w-md bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8">
        <div className="flex items-center gap-3 mb-6 border-b-2 border-black pb-4">
          <UserPlus size={20} />
          <h2 className="font-bold text-lg uppercase tracking-wider">New_User_Registration</h2>
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
            <label className="block text-xs font-bold uppercase mb-2">Full_Name</label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full border-2 border-black p-3 bg-gray-50 focus:bg-white focus:outline-none focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] transition-all font-mono"
              placeholder="Omar Ahmed"
              required
              autoComplete="name"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase mb-2">Email_Address</label>
            <input
              type="email"
              value={email}
              onChange={handleEmailChange}
              className={`w-full border-2 p-3 bg-gray-50 focus:bg-white focus:outline-none transition-all font-mono ${
                emailWarning ? 'border-yellow-500' : 'border-black focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
              }`}
              placeholder="user@alexu.edu.eg"
              required
              autoComplete="email"
            />
            {emailWarning && (
              <div className="mt-2 flex items-center gap-2 text-yellow-600">
                <AlertTriangle size={14} />
                <span className="text-xs">{emailWarning}</span>
              </div>
            )}
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
              minLength={8}
              autoComplete="new-password"
            />
            <p className="mt-1 text-xs opacity-40">Minimum 8 characters</p>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase mb-2">Confirm_Password</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={`w-full border-2 p-3 bg-gray-50 focus:bg-white focus:outline-none transition-all font-mono ${
                confirmPassword && password !== confirmPassword 
                  ? 'border-red-500' 
                  : 'border-black focus:shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]'
              }`}
              placeholder="••••••••"
              required
              autoComplete="new-password"
            />
            {confirmPassword && password !== confirmPassword && (
              <p className="mt-1 text-xs text-red-500">Passwords do not match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isLoading || emailWarning}
            className="w-full py-3 bg-black text-white font-bold border-2 border-black hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 mt-6"
          >
            {isLoading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                CREATING_ACCOUNT...
              </>
            ) : (
              'CREATE_ACCOUNT'
            )}
          </button>
        </form>

        {/* LOGIN LINK */}
        <div className="mt-6 pt-6 border-t-2 border-gray-200 text-center">
          <p className="text-sm opacity-60">
            Already have an account?{' '}
            <Link 
              to="/login" 
              className="font-bold text-black underline underline-offset-4 hover:opacity-70 transition-opacity"
            >
              Login_Here
            </Link>
          </p>
        </div>
      </div>

      {/* FOOTER */}
      <p className="mt-8 text-xs opacity-40">
        Clark_RAG_v1.0 // REGISTRATION_MODULE
      </p>
    </div>
  );
};

export default RegisterPage;
