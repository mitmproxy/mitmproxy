import * as React from "react";

type DocLinkProps = {
    children?: React.ReactNode;
    resource: string;
};

export default function DocsLink({ children, resource }: DocLinkProps) {
    const url = `https://docs.mitmproxy.org/stable/${resource}`;
    return (
        <a target="_blank" href={url} rel="noreferrer">
            {children || <i className="fa fa-question-circle"></i>}
        </a>
    );
}
