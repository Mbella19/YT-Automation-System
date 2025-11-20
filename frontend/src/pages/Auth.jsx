import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { authAPI } from '../services/api'
import NeoButton from '../components/ui/NeoButton'
import NeoInput from '../components/ui/NeoInput'
import NeoCard from '../components/ui/NeoCard'

function Auth() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)

  const [isSignUp, setIsSignUp] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    password: ''
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      let response
      if (isSignUp) {
        response = await authAPI.register(formData)
      } else {
        response = await authAPI.login({
          email: formData.email,
          password: formData.password
        })
      }

      login(response.data.user, response.data.access_token)
      navigate('/decision')
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-neo-bg flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="font-display font-black text-5xl italic tracking-tighter mb-2">TRY ON</h1>
          <p className="font-mono text-sm font-bold uppercase tracking-widest">Virtual Fitting Room</p>
        </div>

        <NeoCard className="bg-white">
          {/* Toggle */}
          <div className="flex border-3 border-black mb-8 p-1 gap-1 bg-gray-100">
            <button
              onClick={() => setIsSignUp(true)}
              className={`flex-1 py-2 font-bold text-sm uppercase transition-all ${isSignUp
                  ? 'bg-neo-primary text-white border-2 border-black shadow-neo-sm'
                  : 'text-gray-500 hover:bg-gray-200'
                }`}
            >
              Sign Up
            </button>
            <button
              onClick={() => setIsSignUp(false)}
              className={`flex-1 py-2 font-bold text-sm uppercase transition-all ${!isSignUp
                  ? 'bg-neo-secondary text-black border-2 border-black shadow-neo-sm'
                  : 'text-gray-500 hover:bg-gray-200'
                }`}
            >
              Log In
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {isSignUp && (
              <NeoInput
                label="Full Name"
                placeholder="YOUR NAME"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              />
            )}

            <NeoInput
              label="Email"
              type="email"
              placeholder="NAME@EXAMPLE.COM"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />

            <NeoInput
              label="Password"
              type="password"
              placeholder="••••••••"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            />

            {error && (
              <div className="bg-red-100 border-3 border-red-500 p-3 font-bold text-red-600 text-sm">
                ⚠️ {error}
              </div>
            )}

            <NeoButton
              type="submit"
              fullWidth
              variant={isSignUp ? 'primary' : 'secondary'}
              disabled={loading}
              className="mt-6"
            >
              {loading ? 'LOADING...' : isSignUp ? 'CREATE ACCOUNT' : 'LOG IN'}
            </NeoButton>
          </form>

          {isSignUp && (
            <p className="text-xs font-mono text-center mt-4 text-gray-500">
              By joining, you agree to our TERMS and PRIVACY POLICY.
            </p>
          )}
        </NeoCard>
      </div>
    </div>
  )
}

export default Auth
