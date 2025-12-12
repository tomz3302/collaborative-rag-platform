import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Box, CheckCircle, XCircle, Loader2 } from 'lucide-react';

const VerifyEmailPage = () => {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('');

  const { verifyEmail } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (!token) {
      setStatus('error');
      setErrorMessage('No verification token provided');
      return;
    }

    const verify = async () => {
      try {
        await verifyEmail(token);
        setStatus('success');
        
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } catch (err) {
        setStatus('error');
        if (err.message === 'VERIFY_USER_BAD_TOKEN') {
          setErrorMessage('Invalid or expired verification token');
        } else if (err.message === 'VERIFY_USER_ALREADY_VERIFIED') {
          setErrorMessage('Email already verified. Please login.');
        } else {
          setErrorMessage(err.message || 'Verification failed');
        }
      }
    };

    verify();
  }, [searchParams, verifyEmail, navigate]);

  return (
    <div className="min-h-screen bg-gray-50 text-black font-mono flex flex-col items-center justify-center p-8">
      
      {/* HEADER */}
      <div className="mb-12 text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-black text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
          <Box size={32} />
        </div>
        <h1 className="text-4xl font-black tracking-tighter">Clark</h1>
        <p className="opacity-60 text-sm">EMAIL_VERIFICATION_PAGE</p>
      </div>

      {/* STATUS CARD */}
      <div className="w-full max-w-md bg-white border-2 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] p-8 text-center">
        
        {/* LOADING STATE */}
        {status === 'loading' && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 text-black border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-6">
              <Loader2 size={32} className="animate-spin" />
            </div>
            <h2 className="text-2xl font-bold mb-4">VERIFYING_EMAIL...</h2>
            <p className="opacity-60">
              Please wait while we verify your email address.
            </p>
          </>
        )}

        {/* SUCCESS STATE */}
        {status === 'success' && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 bg-green-500 text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-6">
              <CheckCircle size={32} />
            </div>
            <h2 className="text-2xl font-bold mb-4">EMAIL_VERIFIED</h2>
            <p className="opacity-60 mb-4">
              Your email has been successfully verified!
            </p>
            <p className="text-sm opacity-40">
              Redirecting to login...
            </p>
          </>
        )}

        {/* ERROR STATE */}
        {status === 'error' && (
          <>
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-500 text-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] mb-6">
              <XCircle size={32} />
            </div>
            <h2 className="text-2xl font-bold mb-4">VERIFICATION_FAILED</h2>
            <p className="opacity-60 mb-6">
              {errorMessage}
            </p>
            <Link
              to="/login"
              className="inline-block px-6 py-3 bg-black text-white font-bold border-2 border-black hover:bg-gray-800 transition-all"
            >
              GO_TO_LOGIN
            </Link>
          </>
        )}
      </div>

      {/* FOOTER */}
      <p className="mt-8 text-xs opacity-40">
        Clark_RAG_v1.0 // VERIFICATION_MODULE
      </p>
    </div>
  );
};

export default VerifyEmailPage;
