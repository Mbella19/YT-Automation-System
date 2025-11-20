import React from 'react';

const NeoInput = ({
    label,
    type = 'text',
    placeholder,
    value,
    onChange,
    name,
    error,
    className = ''
}) => {
    return (
        <div className={`flex flex-col gap-2 ${className}`}>
            {label && (
                <label className="font-display font-bold text-sm uppercase tracking-wider">
                    {label}
                </label>
            )}
            <input
                type={type}
                name={name}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                className={`
          w-full bg-white border-3 border-black p-3 font-mono text-sm
          focus:outline-none focus:shadow-neo focus:-translate-y-1 focus:translate-x-1 transition-all
          placeholder:text-gray-400
          ${error ? 'border-red-500' : ''}
        `}
            />
            {error && (
                <span className="text-red-600 font-bold text-xs">{error}</span>
            )}
        </div>
    );
};

export default NeoInput;
