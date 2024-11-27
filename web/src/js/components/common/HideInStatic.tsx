import * as React from "react";

type HideInStaticProps = {
    children: React.ReactNode;
};

export default function HideInStatic({ children }: HideInStaticProps) {
    // @ts-expect-error unknown property.
    return window.MITMWEB_STATIC ? null : <>{children}</>;
}
