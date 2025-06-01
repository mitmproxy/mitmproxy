import * as React from "react";
import ContentEditor from "../../../components/contentviews/ContentEditor";
import { render } from "../../test-utils";
import { SyntaxHighlight } from "../../../backends/consts";

test("ContentEditor", async () => {
    const { asFragment } = render(
        <ContentEditor initialContent="foo" onChange={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("ContentEditor highlights HTML", async () => {
    const { asFragment } = render(
        <ContentEditor
            initialContent="<p>yay</p>"
            onChange={() => 0}
            language={SyntaxHighlight.XML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("ContentEditor highlights YAML", async () => {
    const { asFragment } = render(
        <ContentEditor
            initialContent="foo: bar"
            onChange={() => 0}
            language={SyntaxHighlight.YAML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("ContentEditor highlights JavaScript", async () => {
    const { asFragment } = render(
        <ContentEditor
            initialContent="alert(1);"
            onChange={() => 0}
            language={SyntaxHighlight.JAVASCRIPT}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("ContentEditor highlights CSS", async () => {
    const { asFragment } = render(
        <ContentEditor
            initialContent="p { color: red; }"
            onChange={() => 0}
            language={SyntaxHighlight.CSS}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
