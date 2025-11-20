import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import NeoCard from '../components/ui/NeoCard'
import NeoButton from '../components/ui/NeoButton'
import { useAuthStore } from '../store/authStore'
import { Flame } from 'lucide-react'

function StyleDuels() {
    const navigate = useNavigate()
    const { token } = useAuthStore()
    const [challenge, setChallenge] = useState(null)
    const [entries, setEntries] = useState([])
    const [myEntry, setMyEntry] = useState(null)
    const [loading, setLoading] = useState(true)
    const [savedLooks, setSavedLooks] = useState([])
    const [showEntryModal, setShowEntryModal] = useState(false)

    useEffect(() => {
        fetchChallenge()
    }, [])

    const fetchChallenge = async () => {
        try {
            const res = await fetch('http://localhost:5001/api/challenges', {
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await res.json()
            setChallenge(data.challenge)
            if (data.challenge) {
                fetchEntries(data.challenge.id)
                fetchSavedLooks()
            }
        } catch (error) {
            console.error('Error fetching challenge:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchEntries = async (challengeId) => {
        try {
            const res = await fetch(`http://localhost:5001/api/challenges/${challengeId}/entries`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await res.json()
            setEntries(data.entries)
        } catch (error) {
            console.error('Error fetching entries:', error)
        }
    }

    const fetchSavedLooks = async () => {
        try {
            const res = await fetch('http://localhost:5001/api/saved-looks', {
                headers: { Authorization: `Bearer ${token}` }
            })
            const data = await res.json()
            setSavedLooks(data.looks)
        } catch (error) {
            console.error('Error fetching saved looks:', error)
        }
    }

    const handleEnterChallenge = async (lookId) => {
        if (!challenge) return

        try {
            const res = await fetch(`http://localhost:5001/api/challenges/${challenge.id}/enter`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ saved_look_id: lookId })
            })

            if (res.ok) {
                alert('Entered challenge successfully!')
                setShowEntryModal(false)
                // Refresh entries
                fetchEntries(challenge.id)
            } else {
                const data = await res.json()
                alert(data.error)
            }
        } catch (error) {
            console.error('Error entering challenge:', error)
        }
    }

    const handleVote = async (entryId) => {
        try {
            const res = await fetch('http://localhost:5001/api/challenges/vote', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ entry_id: entryId })
            })

            if (res.ok) {
                // Remove voted entry from list to show next one
                setEntries(entries.filter(e => e.id !== entryId))
            }
        } catch (error) {
            console.error('Error voting:', error)
        }
    }

    if (loading) return <div>Loading...</div>

    return (
        <div className="h-full flex flex-col gap-3 md:gap-5 pb-20 md:pb-0">
            <div className="flex justify-between items-center shrink-0 px-2 pt-2">
                <h2 className="font-display font-black text-2xl md:text-4xl lg:text-5xl italic tracking-tighter">STYLE DUELS</h2>
                <p className="font-mono text-xs md:text-sm lg:text-base font-bold">DAILY FASHION BATTLES</p>
            </div>

            {challenge && (
                <NeoCard title="TODAY'S THEME" className="bg-yellow-300 shrink-0 mx-2">
                    <h3 className="text-xl md:text-2xl font-bold mb-1 md:mb-2">{challenge.theme}</h3>
                    <p className="font-mono text-xs md:text-sm mb-2 md:mb-4 line-clamp-2">{challenge.description}</p>
                    <div className="flex justify-between items-center">
                        <span className="font-bold text-[10px] md:text-xs bg-black text-white px-2 py-1">
                            ENDS: {new Date(challenge.end_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <NeoButton onClick={() => setShowEntryModal(true)} size="sm" className="text-xs md:text-sm">
                            ENTER CHALLENGE
                        </NeoButton>
                    </div>
                </NeoCard>
            )}

            <div className="flex-1 min-h-0 flex flex-col px-2 pb-2">
                <h3 className="font-bold font-mono text-sm md:text-xl border-b-4 border-black inline-block w-max mb-4 mx-auto">
                    VOTE FOR THE BEST LOOK
                </h3>

                {entries.length > 0 ? (
                    <div className="relative w-full max-w-sm md:max-w-md mx-auto flex-1 min-h-0 flex flex-col">
                        {/* Simple stack for voting - showing top card */}
                        <NeoCard className="bg-white rotate-1 flex-1 flex flex-col min-h-0 p-2 md:p-4">
                            <div className="flex-1 min-h-0 relative border-2 border-black mb-2 md:mb-4">
                                <img
                                    src={`http://localhost:5001${entries[0].saved_look_url}`}
                                    alt="Entry"
                                    className="absolute inset-0 w-full h-full object-cover"
                                />
                            </div>
                            <p className="font-bold mb-2 text-xs md:text-base shrink-0">Style by {entries[0].user_name}</p>
                            <div className="flex gap-2 md:gap-4 shrink-0">
                                <NeoButton
                                    fullWidth
                                    variant="secondary"
                                    onClick={() => setEntries(entries.slice(1))} // Skip
                                    className="py-2 text-xs md:text-sm"
                                >
                                    SKIP
                                </NeoButton>
                                <NeoButton
                                    fullWidth
                                    variant="primary"
                                    onClick={() => handleVote(entries[0].id)}
                                    className="flex items-center justify-center gap-2 py-2 text-xs md:text-sm"
                                >
                                    VOTE <Flame size={16} className="md:w-5 md:h-5" fill="currentColor" />
                                </NeoButton>
                            </div>
                        </NeoCard>
                    </div>
                ) : (
                    <div className="text-center py-10 bg-white border-4 border-black shadow-neo">
                        <p className="font-mono font-bold">No more entries to vote on!</p>
                    </div>
                )}
            </div>

            {/* Entry Modal */}
            {showEntryModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white border-4 border-black shadow-neo p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto">
                        <h3 className="font-bold text-xl mb-4">Select a Look to Enter</h3>
                        <div className="grid grid-cols-2 gap-4">
                            {savedLooks.map(look => (
                                <div key={look.id} className="border-2 border-black p-2 cursor-pointer hover:bg-gray-100" onClick={() => handleEnterChallenge(look.id)}>
                                    <img
                                        src={`http://localhost:5001/uploads/results/${look.result_filename}`}
                                        alt="Look"
                                        className="w-full h-32 object-cover mb-2"
                                    />
                                    <p className="text-xs font-mono">{new Date(look.created_at).toLocaleDateString()}</p>
                                </div>
                            ))}
                        </div>
                        <div className="mt-4 flex justify-end">
                            <NeoButton variant="secondary" onClick={() => setShowEntryModal(false)}>
                                CANCEL
                            </NeoButton>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

export default StyleDuels
