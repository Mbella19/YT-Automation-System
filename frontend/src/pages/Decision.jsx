import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import NeoCard from '../components/ui/NeoCard'
import NeoButton from '../components/ui/NeoButton'
import { useAuthStore } from '../store/authStore'
import { CloudSun, Shirt, Sparkles } from 'lucide-react'

function Decision() {
  const navigate = useNavigate()
  const { token } = useAuthStore()
  const [briefing, setBriefing] = useState(null)

  useEffect(() => {
    const fetchBriefing = async () => {
      try {
        const res = await fetch('http://localhost:5001/api/daily-briefing?location=London', {
          headers: { Authorization: `Bearer ${token}` }
        })
        const data = await res.json()
        setBriefing(data)
      } catch (error) {
        console.error('Error fetching briefing:', error)
      }
    }
    fetchBriefing()
  }, [])

  return (
    <div className="h-full flex flex-col p-2 md:p-4 gap-2 md:gap-4">
      <div className="text-center shrink-0">
        <h2 className="font-display font-black text-2xl md:text-4xl lg:text-5xl italic tracking-tighter">WHAT'S NEXT?</h2>
        <p className="font-mono text-xs md:text-sm lg:text-base font-bold">CHOOSE YOUR PATH</p>
      </div>

      {briefing && (
        <NeoCard className="bg-blue-200 p-3 md:p-4 lg:p-6 shrink-0 -rotate-1 shadow-2xl">
          <div className="flex items-center gap-3 md:gap-4">
            <CloudSun size={32} className="md:w-12 md:h-12 lg:w-16 lg:h-16" strokeWidth={1.5} />
            <div>
              <h3 className="font-bold text-xs md:text-sm lg:text-base uppercase">Daily Style Tip</h3>
              <p className="font-mono text-xs md:text-sm lg:text-base leading-tight line-clamp-1">{briefing.tip}</p>
            </div>
          </div>
        </NeoCard>
      )}

      <div className="flex-1 min-h-0 flex flex-col gap-4 md:gap-6">
        <NeoCard title="TRY-ON" className="bg-white flex-1 flex flex-col justify-center items-center p-4 md:p-8 lg:p-12 min-h-0 rotate-1 shadow-2xl">
          <div className="flex-1 flex items-center justify-center min-h-0">
            <Shirt size={48} className="md:w-20 md:h-20 lg:w-24 lg:h-24" strokeWidth={1} />
          </div>
          <p className="font-mono text-sm md:text-lg lg:text-xl text-center leading-tight mb-3 md:mb-4">
            Instant virtual try-on.
          </p>
          <NeoButton
            onClick={() => navigate('/photos')}
            fullWidth
            variant="primary"
            className="py-3 md:py-4 lg:py-5 text-sm md:text-base lg:text-lg shrink-0"
          >
            START
          </NeoButton>
        </NeoCard>

        <NeoCard title="STYLIST" className="bg-white flex-1 flex flex-col justify-center items-center p-4 md:p-8 lg:p-12 min-h-0 -rotate-2 shadow-2xl">
          <div className="flex-1 flex items-center justify-center min-h-0">
            <Sparkles size={48} className="md:w-20 md:h-20 lg:w-24 lg:h-24" strokeWidth={1} />
          </div>
          <p className="font-mono text-sm md:text-lg lg:text-xl text-center leading-tight mb-3 md:mb-4">
            Get outfit advice.
          </p>
          <NeoButton
            onClick={() => navigate('/style-me')}
            fullWidth
            variant="secondary"
            className="py-3 md:py-4 lg:py-5 text-sm md:text-base lg:text-lg shrink-0"
          >
            STYLIST
          </NeoButton>
        </NeoCard>
      </div>
    </div>
  )
}

export default Decision
