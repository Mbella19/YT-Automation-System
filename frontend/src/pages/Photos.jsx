import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { photosAPI } from '../services/api'
import { Camera } from 'lucide-react'
import NeoButton from '../components/ui/NeoButton'
import NeoCard from '../components/ui/NeoCard'

function Photos() {
  const navigate = useNavigate()
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    fetchPhotos()
  }, [])

  const fetchPhotos = async () => {
    try {
      const response = await photosAPI.getAll()
      setPhotos(response.data.photos)
    } catch (error) {
      console.error('Error fetching photos:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('photo', file)

    try {
      await photosAPI.upload(formData)
      await fetchPhotos()
    } catch (error) {
      console.error('Error uploading photo:', error)
      alert('Failed to upload photo')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('DELETE THIS PHOTO?')) return

    try {
      await photosAPI.delete(id)
      await fetchPhotos()
    } catch (error) {
      console.error('Error deleting photo:', error)
      alert('Failed to delete photo')
    }
  }

  const handleSelect = async (id) => {
    try {
      await photosAPI.select(id)
      await fetchPhotos()
    } catch (error) {
      console.error('Error selecting photo:', error)
    }
  }

  return (
    <div className="h-full flex flex-col gap-3 md:gap-5 pb-20 md:pb-0">
      <div className="flex justify-between items-center shrink-0 px-2 pt-2">
        <h2 className="font-display font-black text-2xl md:text-4xl lg:text-5xl italic tracking-tighter">MY PHOTOS</h2>
        <label className="cursor-pointer">
          <input
            type="file"
            accept="image/*"
            onChange={handleUpload}
            className="hidden"
            disabled={uploading}
          />
          <span className={`
            inline-block font-display font-bold border-3 border-black px-4 py-2 
            bg-neo-primary text-white shadow-neo hover:-translate-y-1 hover:translate-x-1 hover:shadow-neo-lg
            transition-all
            ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
          `}>
            {uploading ? 'UPLOADING...' : '+ UPLOAD'}
          </span>
        </label>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-2">
        {loading ? (
          <div className="text-center font-mono font-bold p-8">LOADING...</div>
        ) : photos.length === 0 ? (
          <NeoCard className="text-center py-12 bg-white h-full flex flex-col justify-center items-center">
            <Camera className="w-16 h-16 md:w-24 md:h-24 mb-4 stroke-black stroke-[1.5]" />
            <h3 className="font-display font-bold text-xl md:text-2xl mb-2">NO PHOTOS YET</h3>
            <p className="font-mono text-sm md:text-base text-gray-600">
              Upload a photo to start your virtual try-on journey.
            </p>
          </NeoCard>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
            {photos.map((photo) => (
              <div key={photo.id} className="relative group">
                <div className={`
                  border-3 border-black bg-white p-2 shadow-neo transition-transform h-full flex flex-col
                  ${photo.is_selected ? 'bg-neo-accent -rotate-1' : 'hover:rotate-1'}
                `}>
                  <div className="aspect-square overflow-hidden border-2 border-black mb-2">
                    <img
                      src={`/${photo.filepath}`}
                      alt="User photo"
                      className="w-full h-full object-cover"
                    />
                  </div>

                  <div className="flex gap-2 mt-auto">
                    {photo.is_selected ? (
                      <div className="flex-1 bg-black text-white font-mono font-bold text-[10px] md:text-xs py-2 text-center">
                        SELECTED
                      </div>
                    ) : (
                      <button
                        onClick={() => handleSelect(photo.id)}
                        className="flex-1 bg-white border-2 border-black font-mono font-bold text-[10px] md:text-xs py-2 hover:bg-gray-100"
                      >
                        SELECT
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(photo.id)}
                      className="px-2 md:px-3 bg-red-500 border-2 border-black text-white font-bold hover:bg-red-600 text-xs"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {photos.length > 0 && (
        <div className="fixed bottom-20 right-4 md:bottom-8 md:right-8 z-40">
          <NeoButton
            onClick={() => navigate('/wardrobe')}
            variant="primary"
            className="rounded-full px-8 py-4 text-lg shadow-neo-lg"
          >
            NEXT STEP →
          </NeoButton>
        </div>
      )}
    </div>
  )
}

export default Photos
