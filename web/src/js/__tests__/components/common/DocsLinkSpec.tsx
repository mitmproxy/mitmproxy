import * as React from "react";
import DocsLink from "../../../components/common/DocsLink";
import { render } from "../../test-utils";

describe("DocsLink Component", () => {
    it("should be able to be rendered with children nodes", () => {
        const { asFragment } = render(<DocsLink resource="bar">foo</DocsLink>);
        expect(asFragment()).toMatchSnapshot();
    });

    it("should be able to be rendered without children nodes", () => {
        const { asFragment } = render(<DocsLink resource="bar"></DocsLink>);
        expect(asFragment()).toMatchSnapshot();
    });
});
