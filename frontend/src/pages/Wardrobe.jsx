import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { clothingAPI } from '../services/api'
import NeoButton from '../components/ui/NeoButton'
import NeoCard from '../components/ui/NeoCard'
import { useAuthStore } from '../store/authStore'
import { Shirt } from 'lucide-react'

const CATEGORIES = ['all', 'tops', 'bottoms', 'dresses', 'outerwear', 'accessories']

function Wardrobe() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [activeCategory, setActiveCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadCategory, setUploadCategory] = useState('tops')
  const [price, setPrice] = useState('')
  const [addMode, setAddMode] = useState('image') // image, text, link
  const [textDescription, setTextDescription] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [generatedPreview, setGeneratedPreview] = useState(null)
  const [refinementPrompt, setRefinementPrompt] = useState('')
  const [isRefining, setIsRefining] = useState(false)
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false)
  const { token } = useAuthStore()

  useEffect(() => {
    fetchItems()
  }, [activeCategory])

  const fetchItems = async () => {
    try {
      const response = await clothingAPI.getAll(activeCategory)
      setItems(response.data.items)
    } catch (error) {
      console.error('Error fetching clothing:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    setUploading(true)
    try {
      if (addMode === 'image') {
        const files = e.target.files
        if (!files || files.length === 0) return

        const formData = new FormData()
        for (let i = 0; i < files.length; i++) {
          formData.append('clothing', files[i])
        }
        formData.append('category', uploadCategory)
        formData.append('price', price)

        await clothingAPI.upload(formData)
        await fetchItems()
        setShowUploadModal(false)
        setPrice('')
      } else if (addMode === 'text') {
        const response = await fetch('http://localhost:5001/api/clothing/generate', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ description: textDescription, category: uploadCategory })
        })
        const data = await response.json()
        if (response.ok) {
          setGeneratedPreview({
            url: data.temp_image_url,
            filename: data.filename
          })
        } else {
          alert(data.error || 'Generation failed')
        }
      } else if (addMode === 'link') {
        await fetch('http://localhost:5001/api/clothing/import', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ url: linkUrl, category: uploadCategory })
        })
        await fetchItems()
        setShowUploadModal(false)
        setLinkUrl('')
      }

      if (addMode !== 'text') {
        setTextDescription('')
      }
    } catch (error) {
      console.error('Error adding clothing:', error)
      alert('Failed to add clothing item')
    } finally {
      setUploading(false)
    }
  }

  const handleRefine = async () => {
    if (!refinementPrompt) return
    setIsRefining(true)
    try {
      const response = await fetch('http://localhost:5001/api/clothing/refine', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          filename: generatedPreview.filename,
          refinement_prompt: refinementPrompt
        })
      })
      const data = await response.json()
      if (response.ok) {
        setGeneratedPreview({
          url: data.temp_image_url,
          filename: data.filename
        })
        setRefinementPrompt('')
      } else {
        alert(data.error || 'Refinement failed')
      }
    } catch (error) {
      console.error('Refinement error:', error)
      alert('Failed to refine image')
    } finally {
      setIsRefining(false)
    }
  }

  const handleSaveGenerated = async () => {
    setUploading(true)
    try {
      const response = await fetch('http://localhost:5001/api/clothing/save-generated', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          filename: generatedPreview.filename,
          category: uploadCategory
        })
      })

      if (response.ok) {
        await fetchItems()
        setShowUploadModal(false)
        setGeneratedPreview(null)
        setTextDescription('')
        setRefinementPrompt('')
      } else {
        const data = await response.json()
        alert(data.error || 'Failed to save item')
      }
    } catch (error) {
      console.error('Save error:', error)
      alert('Failed to save item')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('DELETE THIS ITEM?')) return

    try {
      await clothingAPI.delete(id)
      await fetchItems()
    } catch (error) {
      console.error('Error deleting clothing:', error)
      alert('Failed to delete clothing item')
    }
  }

  return (
    <div className="h-full flex flex-col gap-3 md:gap-5 pb-20 md:pb-0">
      <div className="flex justify-between items-center shrink-0 px-2 pt-2">
        <h2 className="font-display font-black text-2xl md:text-4xl lg:text-5xl italic tracking-tighter">WARDROBE</h2>
        <NeoButton
          onClick={() => {
            setShowUploadModal(true)
            setGeneratedPreview(null)
          }}
          variant="secondary"
          className="px-3 py-1 md:px-4 md:py-2 text-xs md:text-sm"
        >
          + ADD ITEM
        </NeoButton>
      </div>

      {/* Categories */}
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide px-2 shrink-0">
        {CATEGORIES.map((category) => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={`
              font-mono font-bold text-xs md:text-sm uppercase px-4 py-1.5 md:px-5 md:py-2.5 border-2 border-black whitespace-nowrap transition-all
              ${activeCategory === category
                ? 'bg-black text-white shadow-neo-sm -translate-y-1 translate-x-1'
                : 'bg-white text-black hover:bg-gray-100'
              }
            `}
          >
            {category}
          </button>
        ))}
      </div>

      {/* Items Grid */}
      <div className="flex-1 min-h-0 overflow-y-auto px-2 pb-2">
        {loading ? (
          <div className="text-center font-mono font-bold p-8">LOADING...</div>
        ) : items.length === 0 ? (
          <NeoCard className="text-center py-12 bg-white h-full flex flex-col justify-center items-center">
            <div className="flex justify-center mb-4">
              <Shirt size={64} className="md:w-24 md:h-24" strokeWidth={1} />
            </div>
            <h3 className="font-display font-bold text-xl md:text-2xl mb-2">EMPTY WARDROBE</h3>
            <p className="font-mono text-sm md:text-base text-gray-600">
              Add some clothes to get started!
            </p>
          </NeoCard>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 md:gap-4">
            {items.map((item) => (
              <div key={item.id} className="border-3 border-black bg-white p-2 shadow-neo hover:-translate-y-1 hover:translate-x-1 transition-transform flex flex-col">
                <div className="aspect-square overflow-hidden border-2 border-black mb-2 relative group">
                  <img
                    src={`http://localhost:5001/uploads/clothing/${item.filename}`}
                    alt={item.category}
                    className="w-full h-full object-cover"
                  />
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="absolute top-1 right-1 bg-red-500 border-2 border-black text-white p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    🗑
                  </button>
                </div>
                <div className="font-mono text-[10px] md:text-xs font-bold uppercase text-center bg-gray-100 py-1 border-2 border-black mb-auto">
                  {item.category}
                </div>
                <div className="text-center text-[10px] md:text-xs font-mono mt-1">
                  <span className="block font-bold">CPW: £{item.cost_per_wear || item.price || 0}</span>
                  <span className="text-gray-500">{item.wear_count} wears</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Next Step Button */}
      {items.length > 0 && (
        <div className="fixed bottom-20 right-4 md:bottom-8 md:right-8 z-40">
          <NeoButton
            onClick={() => navigate('/tryon')}
            variant="primary"
            className="rounded-full px-7 py-3.5 text-base shadow-neo-lg"
          >
            TRY ON →
          </NeoButton>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
          <NeoCard title="ADD ITEM" className="w-full max-w-md bg-neo-bg max-h-[90vh] overflow-y-auto">
            <div className="space-y-4">
              {/* Mode Switcher - only show if not previewing */}
              {!generatedPreview && (
                <div className="flex gap-2 mb-4">
                  {['image', 'text', 'link'].map(mode => (
                    <button
                      key={mode}
                      onClick={() => setAddMode(mode)}
                      className={`flex-1 py-1.5 text-sm font-bold uppercase border-2 border-black ${addMode === mode ? 'bg-black text-white' : 'bg-white'}`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              )}

              <div className="relative">
                <label className="font-display font-bold text-sm uppercase mb-2 block">CATEGORY</label>
                <button
                  type="button"
                  onClick={() => !generatedPreview && setCategoryDropdownOpen(!categoryDropdownOpen)}
                  className="w-full border-3 border-black p-3.5 font-mono text-sm bg-white text-left uppercase flex justify-between items-center transition-all hover:shadow-neo hover:-translate-y-0.5 hover:translate-x-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={!!generatedPreview}
                >
                  <span>{uploadCategory}</span>
                  <svg className={`w-4 h-4 transition-transform ${categoryDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                {categoryDropdownOpen && (
                  <div className="absolute z-50 w-full mt-1 border-3 border-black bg-white shadow-neo">
                    {CATEGORIES.filter(c => c !== 'all').map((category) => (
                      <button
                        key={category}
                        type="button"
                        onClick={() => {
                          setUploadCategory(category)
                          setCategoryDropdownOpen(false)
                        }}
                        className={`w-full p-3 font-mono text-sm uppercase text-left border-b-2 border-black last:border-b-0 transition-all ${uploadCategory === category
                          ? 'bg-black text-white'
                          : 'bg-white hover:bg-gray-100'
                          }`}
                      >
                        {category}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Generated Preview UI */}
              {generatedPreview ? (
                <div className="space-y-2">
                  <div className="border-2 border-black bg-white p-1 flex justify-center bg-gray-50">
                    <img
                      src={`http://localhost:5001${generatedPreview.url}`}
                      alt="Generated Preview"
                      className="h-48 w-auto object-contain"
                    />
                  </div>

                  <div>
                    <label className="font-display font-bold text-xs uppercase mb-1 block">REFINE DESIGN</label>
                    <textarea
                      value={refinementPrompt}
                      onChange={(e) => setRefinementPrompt(e.target.value)}
                      className="w-full border-2 border-black p-2 font-mono text-xs h-12 resize-none"
                      placeholder="e.g. Add a red logo..."
                    />
                    <NeoButton
                      onClick={handleRefine}
                      fullWidth
                      disabled={isRefining || !refinementPrompt}
                      variant="secondary"
                      className="mt-1 py-2 text-xs"
                    >
                      {isRefining ? 'REFINING...' : '✨ REFINE'}
                    </NeoButton>
                  </div>

                  <div className="flex gap-2 pt-1">
                    <NeoButton
                      onClick={() => setGeneratedPreview(null)}
                      variant="outline"
                      className="flex-1 py-2 text-xs"
                    >
                      DISCARD
                    </NeoButton>
                    <NeoButton
                      onClick={handleSaveGenerated}
                      variant="primary"
                      className="flex-1 py-2 text-xs"
                      disabled={uploading}
                    >
                      {uploading ? 'SAVING...' : 'ADD'}
                    </NeoButton>
                  </div>
                </div>
              ) : (
                /* Normal Input UI */
                <>
                  {addMode === 'image' && (
                    <>
                      <div>
                        <label className="font-display font-bold text-sm uppercase mb-2 block">PRICE (£)</label>
                        <input
                          type="number"
                          value={price}
                          onChange={(e) => setPrice(e.target.value)}
                          className="w-full border-3 border-black p-3.5 font-mono text-sm"
                          placeholder="0.00"
                        />
                      </div>
                      <label className="block w-full border-3 border-black border-dashed p-8 text-center bg-white cursor-pointer hover:bg-gray-50">
                        <input
                          type="file"
                          accept="image/*"
                          multiple
                          onChange={handleUpload}
                          className="hidden"
                          disabled={uploading}
                        />
                        <span className="font-mono font-bold text-sm">
                          {uploading ? 'UPLOADING & PROCESSING...' : 'CLICK TO UPLOAD IMAGE(S)'}
                        </span>
                      </label>
                    </>
                  )}

                  {addMode === 'text' && (
                    <div>
                      <label className="font-display font-bold text-sm uppercase mb-2 block">DESCRIPTION</label>
                      <textarea
                        value={textDescription}
                        onChange={(e) => setTextDescription(e.target.value)}
                        className="w-full border-3 border-black p-3.5 font-mono text-sm h-24"
                        placeholder="e.g. Blue denim jacket with silver buttons"
                      />
                      <NeoButton onClick={handleUpload} fullWidth disabled={uploading} className="mt-2">
                        {uploading ? 'GENERATING PREVIEW...' : 'GENERATE PREVIEW'}
                      </NeoButton>
                    </div>
                  )}

                  {addMode === 'link' && (
                    <div>
                      <label className="font-display font-bold text-sm uppercase mb-2 block">PRODUCT URL</label>
                      <input
                        type="text"
                        value={linkUrl}
                        onChange={(e) => setLinkUrl(e.target.value)}
                        className="w-full border-3 border-black p-3.5 font-mono text-sm"
                        placeholder="https://..."
                      />
                      <NeoButton onClick={handleUpload} fullWidth disabled={uploading} className="mt-2">
                        {uploading ? 'IMPORTING...' : 'IMPORT FROM URL'}
                      </NeoButton>
                    </div>
                  )}

                  <div className="flex gap-2 pt-4">
                    <NeoButton
                      onClick={() => setShowUploadModal(false)}
                      variant="outline"
                      className="flex-1"
                    >
                      CANCEL
                    </NeoButton>
                  </div>
                </>
              )}
            </div>
          </NeoCard>
        </div>
      )}
    </div>
  )
}

export default Wardrobe
