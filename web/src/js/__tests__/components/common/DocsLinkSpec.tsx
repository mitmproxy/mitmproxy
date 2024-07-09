import * as React from "react";
import renderer from "react-test-renderer";
import DocsLink from "../../../components/common/DocsLink";

describe("DocsLink Component", () => {
    it("should be able to be rendered with children nodes", () => {
        const docsLink = renderer.create(
            <DocsLink resource="bar">foo</DocsLink>,
        );
        const tree = docsLink.toJSON();
        expect(tree).toMatchSnapshot();
    });

    it("should be able to be rendered without children nodes", () => {
        const docsLink = renderer.create(<DocsLink resource="bar"></DocsLink>);
        const tree = docsLink.toJSON();
        expect(tree).toMatchSnapshot();
    });
});
