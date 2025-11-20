import { useState, useRef, useEffect } from 'react'
import { ChevronDown } from 'lucide-react'

const NeoSelect = ({ value, onChange, options, className = '', placeholder = 'SELECT' }) => {
    const [isOpen, setIsOpen] = useState(false)
    const containerRef = useRef(null)

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (containerRef.current && !containerRef.current.contains(event.target)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    return (
        <div className={`relative ${className}`} ref={containerRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full h-full flex items-center justify-between px-2 py-2 font-mono font-bold bg-transparent hover:bg-gray-50 transition-colors outline-none cursor-pointer"
            >
                <span className="truncate">{value || placeholder}</span>
                <ChevronDown size={16} className={`ml-1 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute top-full left-[-2px] right-[-2px] max-h-60 overflow-y-auto bg-white border-3 border-black shadow-neo z-50 mt-1">
                    {options.map((option) => {
                        const optionValue = typeof option === 'object' ? option.value : option
                        const optionLabel = typeof option === 'object' ? option.label : option

                        return (
                            <button
                                key={optionValue}
                                type="button"
                                onClick={() => {
                                    onChange(optionValue)
                                    setIsOpen(false)
                                }}
                                className={`
                  w-full text-left px-3 py-2 font-mono font-bold transition-colors border-b-2 border-gray-100 last:border-0
                  ${value === optionValue ? 'bg-neo-accent' : 'hover:bg-gray-100'}
                `}
                            >
                                {optionLabel}
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
    )
}

export default NeoSelect
