import React from 'react'

export default function HideInStatic({className, children }) {
    return MITMWEB_STATIC ? null : ( <div className={className}>{children}</div> )
}
