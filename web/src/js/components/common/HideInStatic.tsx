import * as React from "react"

type HideInStaticProps = {
    children: React.ReactNode,
}

export default function HideInStatic({ children }: HideInStaticProps) {
    // @ts-ignore
    return (window.MITMWEB_CONF && window.MITMWEB_CONF.static) ? null : <>{children}</>
}
