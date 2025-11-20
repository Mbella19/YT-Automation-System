import { useNavigate } from 'react-router-dom'
import NeoButton from '../components/ui/NeoButton'

function Welcome() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-neo-bg flex flex-col relative overflow-hidden">
      {/* Decorative Elements */}
      <div className="absolute top-[-50px] right-[-50px] w-40 h-40 bg-neo-primary rounded-full border-3 border-black"></div>
      <div className="absolute bottom-[10%] left-[-20px] w-20 h-20 bg-neo-secondary transform rotate-45 border-3 border-black"></div>

      {/* Header */}
      <header className="p-6 flex justify-between items-center z-10">
        <h2 className="font-display font-black text-2xl italic tracking-tighter">TRY ON</h2>
        <div className="font-mono text-xs font-bold border-2 border-black px-2 py-1 bg-white">BETA</div>
      </header>

      {/* Hero Section */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 z-10">
        <div className="max-w-md w-full text-center space-y-8">
          <div className="relative inline-block">
            <h1 className="font-display font-black text-6xl md:text-8xl leading-[0.8] tracking-tighter text-black relative z-10">
              VIRTUAL<br />FITTING<br />ROOM
            </h1>
            <div className="absolute top-2 left-2 w-full h-full bg-white border-3 border-black -z-0"></div>
          </div>

          <div className="bg-white border-3 border-black p-4 shadow-neo rotate-1 max-w-xs mx-auto">
            <p className="font-mono text-sm font-bold leading-tight">
              STOP GUESSING. START WEARING.
              USE AI TO TRY ON CLOTHES INSTANTLY.
            </p>
          </div>

          <div className="pt-8">
            <NeoButton
              onClick={() => navigate('/auth')}
              variant="primary"
              className="text-xl px-12 py-4 w-full md:w-auto"
            >
              START NOW →
            </NeoButton>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 text-center z-10">
        <p className="font-mono text-xs font-bold">
          POWERED BY GOOGLE GEMINI
        </p>
      </div>
    </div>
  )
}

export default Welcome
