import React from 'react';

const NeoCard = ({ children, className = '', title }) => {
    return (
        <div className={`bg-white border-3 border-black shadow-neo p-6 ${className}`}>
            {title && (
                <h3 className="font-display font-bold text-xl mb-4 border-b-3 border-black pb-2">
                    {title}
                </h3>
            )}
            {children}
        </div>
    );
};

export default NeoCard;
