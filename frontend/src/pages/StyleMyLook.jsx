import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import axios from 'axios'
import NeoButton from '../components/ui/NeoButton'
import NeoInput from '../components/ui/NeoInput'
import NeoCard from '../components/ui/NeoCard'
import NeoSelect from '../components/ui/NeoSelect'

import { MapPin } from 'lucide-react'

function StyleMyLook() {
  const navigate = useNavigate()
  const [occasion, setOccasion] = useState('')
  const [location, setLocation] = useState('')
  const [hour, setHour] = useState('09')
  const [minute, setMinute] = useState('15')
  const [period, setPeriod] = useState('AM')
  const [considerWeather, setConsiderWeather] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [results, setResults] = useState([])
  const [weatherSummary, setWeatherSummary] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  const handleGetLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          try {
            const response = await axios.get(
              `https://nominatim.openstreetmap.org/reverse?lat=${position.coords.latitude}&lon=${position.coords.longitude}&format=json`
            )
            const city = response.data.address.city || response.data.address.town || response.data.address.state
            const state = response.data.address.state
            setLocation(`${city}, ${state}`)
          } catch (error) {
            console.error('Error getting location:', error)
          }
        },
        (error) => {
          console.error('Error getting location:', error)
          alert('UNABLE TO GET LOCATION')
        }
      )
    } else {
      alert('GEOLOCATION NOT SUPPORTED')
    }
  }

  const handleGenerate = async () => {
    if (!occasion.trim() || !location.trim()) {
      alert('PLEASE FILL ALL FIELDS')
      return
    }

    setErrorMessage('')
    setResults([])
    setWeatherSummary(null)
    setGenerating(true)

    try {
      const time = `${hour}:${minute} ${period}`
      const response = await api.post('/style-me', {
        occasion: occasion.trim(),
        location: location.trim(),
        time,
        consider_weather: considerWeather
      })

      setResults(response.data.outfits || [])
      setWeatherSummary(response.data.weather || null)
    } catch (error) {
      console.error('Error generating style:', error)
      setErrorMessage('FAILED TO GENERATE STYLE')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-6 pb-24">
      <div className="text-center mb-8">
        <h2 className="font-display font-black text-4xl italic tracking-tighter">AI STYLIST</h2>
        <p className="font-mono text-sm font-bold">LET US STYLE YOU</p>
      </div>

      <NeoCard className="bg-white">
        <div className="space-y-4">
          <NeoInput
            label="OCCASION"
            placeholder="E.G. DINNER DATE"
            value={occasion}
            onChange={(e) => setOccasion(e.target.value)}
          />

          <div className="flex gap-2">
            <div className="flex-1">
              <label className="font-display font-bold text-sm uppercase tracking-wider block mb-2">TIME</label>
              <div className="flex border-3 border-black bg-white">
                <div className="flex-1">
                  <NeoSelect
                    value={hour}
                    onChange={setHour}
                    options={Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0'))}
                  />
                </div>
                <div className="border-l-3 border-black"></div>
                <div className="flex-1">
                  <NeoSelect
                    value={minute}
                    onChange={setMinute}
                    options={['00', '15', '30', '45']}
                  />
                </div>
                <div className="border-l-3 border-black"></div>
                <div className="flex-1">
                  <NeoSelect
                    value={period}
                    onChange={setPeriod}
                    options={['AM', 'PM']}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="relative">
            <NeoInput
              label="LOCATION"
              placeholder="E.G. NEW YORK"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            <button
              type="button"
              onClick={handleGetLocation}
              className="absolute right-2 top-8 p-1.5 bg-neo-accent border-2 border-black shadow-neo-sm hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px] transition-all active:bg-neo-primary active:text-white group"
              title="Get Current Location"
            >
              <MapPin size={18} className="text-black group-active:text-white" />
            </button>
          </div>

          <label className="flex items-center gap-3 border-3 border-black p-3 cursor-pointer hover:bg-gray-50">
            <input
              type="checkbox"
              checked={considerWeather}
              onChange={(e) => setConsiderWeather(e.target.checked)}
              className="w-6 h-6 border-3 border-black rounded-none text-black focus:ring-0"
            />
            <span className="font-mono font-bold uppercase">CONSIDER WEATHER</span>
          </label>

          <NeoButton
            onClick={handleGenerate}
            disabled={generating}
            fullWidth
            variant="primary"
            className="mt-4"
          >
            {generating ? 'GENERATING...' : 'GENERATE STYLE'}
          </NeoButton>
        </div>
      </NeoCard>

      {weatherSummary && (
        <div className="bg-neo-secondary border-3 border-black p-4 shadow-neo">
          <h3 className="font-display font-bold uppercase mb-1">WEATHER INSIGHT</h3>
          <p className="font-mono text-sm">
            {weatherSummary.temperature}°{weatherSummary.temperature_unit} · {weatherSummary.conditions}
          </p>
        </div>
      )}

      {errorMessage && (
        <div className="bg-red-100 border-3 border-black p-4 text-red-600 font-bold text-center">
          {errorMessage}
        </div>
      )}

      {results.map((outfit, index) => (
        <NeoCard key={index} title={`OUTFIT ${index + 1}`} className="bg-white">
          {outfit.image_url && (
            <div className="border-3 border-black mb-4">
              <img src={outfit.image_url} alt="Outfit" className="w-full" />
            </div>
          )}
          <h3 className="font-display font-black text-xl mb-2">{outfit.name}</h3>
          <p className="font-mono text-sm mb-4">{outfit.description}</p>

          <div className="space-y-2">
            <p className="font-bold text-xs uppercase bg-black text-white inline-block px-2 py-1">PIECES</p>
            <ul className="space-y-1">
              {(outfit.items || []).map((item) => (
                <li key={item.id} className="flex justify-between border-b-2 border-gray-100 py-1 font-mono text-sm">
                  <span>{item.display_name || item.filename}</span>
                  <span className="text-gray-500 uppercase text-xs">{item.category}</span>
                </li>
              ))}
            </ul>
          </div>
        </NeoCard>
      ))}
    </div>
  )
}

export default StyleMyLook
