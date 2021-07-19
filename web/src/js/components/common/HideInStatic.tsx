import React from 'react'

type HideInStaticProps = {
    children: React.ReactNode,
}

export default function HideInStatic({ children }: HideInStaticProps) {
    return (window.MITMWEB_CONF && window.MITMWEB_CONF.static) ? null : <>{[children]}</>
}
