import React from 'react'

export default function HideInStatic({ children }) {
    return window.MITMWEB_STATIC ? null : [children]
}
