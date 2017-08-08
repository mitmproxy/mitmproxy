import React from 'react'

export default function HideInStatic({ children }) {
    return global.MITMWEB_STATIC ? null : [children]
}
