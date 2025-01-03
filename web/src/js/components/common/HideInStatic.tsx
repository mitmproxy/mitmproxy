import * as React from "react";

type HideInStaticProps = {
    children: React.ReactNode;
};

export default function HideInStatic({ children }: HideInStaticProps) {
    return window.MITMWEB_STATIC ? null : <>{children}</>;
}
