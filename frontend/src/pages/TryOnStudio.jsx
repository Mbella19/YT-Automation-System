import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { photosAPI, clothingAPI, tryonAPI } from '../services/api'
import NeoButton from '../components/ui/NeoButton'
import NeoCard from '../components/ui/NeoCard'
import { MousePointerClick, Sparkles } from 'lucide-react'

function TryOnStudio() {
  const navigate = useNavigate()
  const [photos, setPhotos] = useState([])
  const [clothingItems, setClothingItems] = useState([])
  const [selectedPhoto, setSelectedPhoto] = useState(null)
  const [selectedClothing, setSelectedClothing] = useState(null)
  const [activeTab, setActiveTab] = useState('photos')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [photosRes, clothingRes] = await Promise.all([
        photosAPI.getAll(),
        clothingAPI.getAll('all')
      ])
      setPhotos(photosRes.data.photos)
      setClothingItems(clothingRes.data.items)

      const selected = photosRes.data.photos.find(p => p.is_selected)
      if (selected) setSelectedPhoto(selected)
    } catch (error) {
      console.error('Error fetching data:', error)
    }
  }

  const handleTryOn = async () => {
    if (!selectedPhoto || !selectedClothing) {
      alert('SELECT BOTH A PHOTO AND CLOTHING ITEM')
      return
    }

    setGenerating(true)
    try {
      const response = await tryonAPI.generate({
        photo_id: selectedPhoto.id,
        clothing_id: selectedClothing.id
      })
      setResult(response.data.result)
    } catch (error) {
      console.error('Error generating try-on:', error)
      alert('FAILED TO GENERATE TRY-ON')
    } finally {
      setGenerating(false)
    }
  }

  const currentItems = activeTab === 'photos' ? photos : clothingItems

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] md:h-[calc(100vh-100px)] overflow-hidden pb-1">
      {/* Header */}
      <div className="flex justify-between items-center mb-1 md:mb-2 shrink-0">
        <h2 className="font-display font-black text-base md:text-2xl lg:text-3xl italic tracking-tighter">STUDIO</h2>
        <div className="flex gap-2">
          <NeoButton
            onClick={() => navigate('/saved')}
            variant="outline"
            className="px-3 py-2 text-xs"
          >
            SAVED LOOKS
          </NeoButton>
        </div>
      </div>

      {/* Main Display Area */}
      <div className="flex-[0.8] min-h-0 bg-white border-2 md:border-3 border-black shadow-neo p-0.5 md:p-1.5 mb-0.5 md:mb-1.5 relative overflow-hidden">
        {result ? (
          <img
            src={`/${result.result_filepath}`}
            alt="Try-on result"
            className="w-full h-full object-contain bg-gray-100"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-gray-100 border-2 border-dashed border-gray-300">
            <div className="mb-1">
              {selectedPhoto && selectedClothing ? (
                <Sparkles size={26} className="md:w-12 md:h-12" strokeWidth={1} />
              ) : (
                <MousePointerClick size={26} className="md:w-12 md:h-12" strokeWidth={1} />
              )}
            </div>
            <p className="font-mono text-[11px] md:text-xs font-bold text-center max-w-xs">
              {selectedPhoto && selectedClothing
                ? 'READY TO GENERATE!'
                : 'SELECT A PHOTO AND CLOTHING ITEM BELOW'}
            </p>
          </div>
        )}

        {/* Selection Indicators */}
        <div className="absolute top-1.5 left-1.5 flex flex-col gap-1.5">
          {selectedPhoto && (
            <div className="bg-neo-primary text-white font-mono text-xs font-bold px-2 py-1 border-2 border-black shadow-neo-sm">
              PHOTO SELECTED
            </div>
          )}
          {selectedClothing && (
            <div className="bg-neo-secondary text-black font-mono text-xs font-bold px-2 py-1 border-2 border-black shadow-neo-sm">
              CLOTHING SELECTED
            </div>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="bg-white border-3 border-black p-2 shadow-neo shrink-0">
        {/* Tabs */}
        <div className="flex border-b-3 border-black mb-1">
          <button
            onClick={() => setActiveTab('photos')}
            className={`flex-1 font-mono font-bold text-sm py-2 ${activeTab === 'photos' ? 'bg-neo-accent' : 'hover:bg-gray-100'
              }`}
          >
            PHOTOS
          </button>
          <div className="w-0.5 bg-black"></div>
          <button
            onClick={() => setActiveTab('wardrobe')}
            className={`flex-1 font-mono font-bold text-sm py-2 ${activeTab === 'wardrobe' ? 'bg-neo-secondary' : 'hover:bg-gray-100'
              }`}
          >
            WARDROBE
          </button>
        </div>

        {/* Carousel */}
        <div className="overflow-x-auto whitespace-nowrap pb-2 scrollbar-hide">
          <div className="flex gap-2">
            {currentItems.map((item) => {
              const isSelected = activeTab === 'photos'
                ? selectedPhoto?.id === item.id
                : selectedClothing?.id === item.id

              return (
                <button
                  key={item.id}
                  onClick={() => activeTab === 'photos' ? setSelectedPhoto(item) : setSelectedClothing(item)}
                  className={`
                    inline-block w-12 h-12 md:w-20 md:h-20 border-2 border-black flex-shrink-0 transition-all
                    ${isSelected ? 'ring-2 md:ring-4 ring-black scale-95' : 'hover:scale-95'}
                  `}
                >
                  <img
                    src={`http://localhost:5001/uploads/${activeTab === 'photos' ? 'photos' : 'clothing'}/${item.filename}`}
                    alt="Item"
                    className="w-full h-full object-cover"
                  />
                </button>
              )
            })}
            {currentItems.length === 0 && (
              <div className="w-full py-4 text-center font-mono text-xs text-gray-500">
                NO ITEMS FOUND
              </div>
            )}
          </div>
        </div>

        {/* Action Button */}
        <NeoButton
          onClick={handleTryOn}
          disabled={generating || !selectedPhoto || !selectedClothing}
          fullWidth
          variant="primary"
          className="mt-1 md:mt-2 py-2 md:py-3 text-xs md:text-sm"
        >
          {generating ? 'GENERATING...' : 'TRY ON NOW'}
        </NeoButton>
      </div>
    </div>
  )
}

export default TryOnStudio
