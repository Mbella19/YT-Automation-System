import React, { useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { Home, Shirt, Sparkles, Camera, LogOut, Swords } from 'lucide-react';

const Layout = ({ children }) => {
    const location = useLocation();
    const navigate = useNavigate();
    const logout = useAuthStore((state) => state.logout);

    const isActive = (path) => location.pathname === path;

    const navItems = [
        { path: '/decision', label: 'Home', icon: Home },
        { path: '/wardrobe', label: 'Wardrobe', icon: Shirt },
        { path: '/photos', label: 'Photos', icon: Camera },
        { path: '/duels', label: 'Duels', icon: Swords },
        { path: '/saved', label: 'Looks', icon: Camera },
    ];

    const handleLogout = () => {
        logout();
        navigate('/auth');
    };

    return (
        <div className="min-h-screen bg-neo-bg flex flex-col pb-20 md:pb-0">
            {/* Top Bar */}
            <header className="bg-white border-b-3 border-black p-4 flex justify-between items-center sticky top-0 z-50">
                <Link
                    to="/"
                    className="cursor-pointer group"
                    aria-label="Return to the main home screen"
                >
                    <h1 className="font-display font-black text-2xl tracking-tighter italic group-hover:text-neo-primary transition-colors">TRY ON</h1>
                </Link>
                <div className="flex items-center gap-4">
                    <div className="bg-black text-white px-2 py-1 font-mono text-xs font-bold">
                        CREDITS: {useAuthStore(state => state.user?.credits || 0)}
                    </div>
                    <button
                        onClick={handleLogout}
                        className="font-mono text-xs font-bold underline hover:text-neo-primary flex items-center gap-1"
                    >
                        LOGOUT <LogOut size={14} strokeWidth={3} />
                    </button>
                </div>
            </header>

            {/* Main Content */}
            < main className="flex-1 p-4 max-w-md mx-auto w-full md:max-w-2xl lg:max-w-4xl" >
                {children}
            </main >

            {/* Mobile Bottom Nav */}
            < nav className="fixed bottom-0 left-0 right-0 bg-white border-t-3 border-black p-2 grid grid-cols-5 gap-1 z-50 md:hidden" >
                {
                    navItems.map((item) => {
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`
              flex flex-col items-center justify-center p-2 border-2 transition-all
              ${isActive(item.path)
                                        ? 'bg-neo-accent border-black shadow-neo-sm -translate-y-1'
                                        : 'border-transparent hover:bg-gray-100'
                                    }
            `}
                            >
                                <Icon size={24} strokeWidth={3} />
                                <span className="font-display font-bold text-[10px] uppercase mt-1">{item.label}</span>
                            </Link>
                        );
                    })
                }
            </nav >

            {/* Desktop Sidebar (Hidden on mobile) */}
            < div className="hidden md:flex fixed left-0 top-[70px] bottom-0 w-64 border-r-3 border-black bg-white flex-col p-4 gap-4" >
                {
                    navItems.map((item) => {
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.path}
                                to={item.path}
                                className={`
              flex items-center gap-4 p-4 border-3 transition-all font-bold
              ${isActive(item.path)
                                        ? 'bg-neo-accent border-black shadow-neo'
                                        : 'bg-white border-black hover:translate-x-1 hover:shadow-neo-sm'
                                    }
            `}
                            >
                                <Icon size={28} strokeWidth={3} />
                                <span className="font-display uppercase tracking-wider">{item.label}</span>
                            </Link>
                        );
                    })
                }
            </div >
        </div >
    );
};

export default Layout;
