import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';

/**
 * AuthOverlay - Glassmorphism login/register modal.
 */
function AuthOverlay({ mode, setMode, onClose, onSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const url = mode === 'login' 
      ? 'http://localhost:8000/api/auth/login/' 
      : 'http://localhost:8000/api/auth/register/';

    const payload = mode === 'login' 
      ? { username, password } 
      : { username, password, email };

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || (data.username ? `Username: ${data.username[0]}` : 'Auth failed'));
      }

      if (mode === 'login') {
        localStorage.setItem('fq-token', data.access);
        localStorage.setItem('fq-refresh', data.refresh);
        localStorage.setItem('fq-user', username);
        onSuccess();
      } else {
        // After registration, switch to login
        setMode('login');
        setError('Account created! Please log in.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-card">
        <button className="close-auth" onClick={onClose}>
          <X size={24} />
        </button>

        <div className="auth-header">
          <h2>{mode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
          <p>{mode === 'login' ? 'Enter your credentials to continue' : 'Join FinQuery AI to start analyzing'}</p>
        </div>

        {error && <div style={{ color: '#ef4444', marginBottom: '1.5rem', fontSize: '0.9rem' }}>{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input 
              type="text" 
              required 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="johndoe" 
            />
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label>Email Address</label>
              <input 
                type="email" 
                required 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="john@example.com" 
              />
            </div>
          )}

          <div className="form-group">
            <label>Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" 
            />
          </div>

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? <Loader2 className="animate-spin mx-auto" size={20} /> : (mode === 'login' ? 'Log In' : 'Sign Up')}
          </button>
        </form>

        <div className="auth-switch">
          {mode === 'login' ? (
            <>Don't have an account?<span onClick={() => setMode('register')}>Create one</span></>
          ) : (
            <>Already have an account?<span onClick={() => setMode('login')}>Log in</span></>
          )}
        </div>
      </div>
    </div>
  );
}

export default AuthOverlay;
