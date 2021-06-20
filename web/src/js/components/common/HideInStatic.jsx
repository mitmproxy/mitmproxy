import React from 'react'

export default function HideInStatic({ children }) {
    return (window.MITMWEB_CONF && window.MITMWEB_CONF.static) ? null : [children]
}
