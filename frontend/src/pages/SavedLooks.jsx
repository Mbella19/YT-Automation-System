import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { tryonAPI } from '../services/api'
import NeoButton from '../components/ui/NeoButton'
import NeoCard from '../components/ui/NeoCard'
import { Camera } from 'lucide-react'

function SavedLooks() {
  const navigate = useNavigate()
  const [looks, setLooks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLooks()
  }, [])

  const fetchLooks = async () => {
    try {
      const response = await tryonAPI.getSaved()
      setLooks(response.data.looks)
    } catch (error) {
      console.error('Error fetching saved looks:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('DELETE THIS LOOK?')) return

    try {
      await tryonAPI.deleteSaved(id)
      await fetchLooks()
    } catch (error) {
      console.error('Error deleting look:', error)
      alert('Failed to delete look')
    }
  }

  return (
    <div className="h-full flex flex-col gap-3 md:gap-5 pb-20 md:pb-0">
      <div className="flex justify-between items-center shrink-0 px-2 pt-2">
        <h2 className="font-display font-black text-2xl md:text-4xl lg:text-5xl italic tracking-tighter">MY LOOKS</h2>
        <NeoButton
          onClick={() => navigate('/tryon')}
          variant="secondary"
          className="px-3 md:px-4 py-1.5 md:py-2 text-xs md:text-sm"
        >
          + NEW LOOK
        </NeoButton>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-2">
        {loading ? (
          <div className="text-center font-mono font-bold p-8">LOADING...</div>
        ) : looks.length === 0 ? (
          <NeoCard className="text-center py-12 bg-white h-full flex flex-col justify-center items-center">
            <div className="flex justify-center mb-4">
              <Camera size={64} className="md:w-24 md:h-24" strokeWidth={1} />
            </div>
            <h3 className="font-display font-bold text-xl md:text-2xl mb-2">NO SAVED LOOKS</h3>
            <p className="font-mono text-sm md:text-base text-gray-600">
              Create your first virtual try-on to see it here!
            </p>
          </NeoCard>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
            {looks.map((look) => (
              <div key={look.id} className="border-3 border-black bg-white p-2 shadow-neo hover:-translate-y-1 hover:translate-x-1 transition-transform flex flex-col">
                <div className="relative aspect-[3/4] border-2 border-black mb-2">
                  <img
                    src={`/${look.result_filepath}`}
                    alt="Saved look"
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex gap-2 mt-auto">
                  <NeoButton
                    onClick={() => handleDelete(look.id)}
                    variant="ghost"
                    className="flex-1 bg-red-100 hover:bg-red-200 text-red-600 font-bold border-2 border-black text-[10px] md:text-xs py-1"
                  >
                    DELETE
                  </NeoButton>
                  <NeoButton
                    onClick={() => window.open(`/${look.result_filepath}`, '_blank')}
                    variant="outline"
                    className="flex-1 border-2 border-black text-[10px] md:text-xs py-1"
                  >
                    VIEW
                  </NeoButton>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default SavedLooks
