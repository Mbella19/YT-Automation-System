import React from 'react';

const NeoButton = ({
    children,
    onClick,
    variant = 'primary',
    className = '',
    type = 'button',
    disabled = false,
    fullWidth = false
}) => {
    const baseStyles = "font-display font-bold border-3 border-black px-6 py-3 transition-all duration-200 active:translate-x-[2px] active:translate-y-[2px] active:shadow-none disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-neo-primary text-white shadow-neo hover:-translate-y-1 hover:translate-x-1 hover:shadow-neo-lg",
        secondary: "bg-neo-secondary text-black shadow-neo hover:-translate-y-1 hover:translate-x-1 hover:shadow-neo-lg",
        accent: "bg-neo-accent text-black shadow-neo hover:-translate-y-1 hover:translate-x-1 hover:shadow-neo-lg",
        outline: "bg-white text-black shadow-neo hover:-translate-y-1 hover:translate-x-1 hover:shadow-neo-lg",
        ghost: "bg-transparent border-none shadow-none hover:bg-black/5"
    };

    return (
        <button
            type={type}
            onClick={onClick}
            disabled={disabled}
            className={`
        ${baseStyles} 
        ${variants[variant]} 
        ${fullWidth ? 'w-full' : ''} 
        ${className}
      `}
        >
            {children}
        </button>
    );
};

export default NeoButton;
