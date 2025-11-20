/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "neo-bg": "#FDFD96", // Pastel Yellow background
        "neo-text": "#050505", // Almost black
        "neo-primary": "#FF6B6B", // Pastel Red
        "neo-secondary": "#4ECDC4", // Teal
        "neo-accent": "#FFD93D", // Yellow accent
        "neo-white": "#FFFFFF",
        "neo-black": "#000000",
      },
      fontFamily: {
        "display": ["Plus Jakarta Sans", "sans-serif"],
        "mono": ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        "neo": "4px 4px 0px 0px rgba(0,0,0,1)",
        "neo-sm": "2px 2px 0px 0px rgba(0,0,0,1)",
        "neo-lg": "8px 8px 0px 0px rgba(0,0,0,1)",
      },
      borderWidth: {
        "3": "3px",
      },
      borderRadius: {
        "base": "0px", // Sharp edges usually, but maybe slight round for "unpolished" feel? Let's go sharp or slight. User said "unpolished edges".
        "neo": "0.375rem",
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

