import * as React from "react";
import Icon from "./Icon";

type DocLinkProps = {
    children?: React.ReactNode;
    resource: string;
};

export default function DocsLink({ children, resource }: DocLinkProps) {
    const url = `https://docs.mitmproxy.org/stable/${resource}`;
    return (
        <a className="docs-link" target="_blank" href={url} rel="noreferrer">
            {children || <Icon name="help" />}
        </a>
    );
}
