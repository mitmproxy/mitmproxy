import * as React from "react";
import CodeEditor from "../../../components/contentviews/CodeEditor";
import { render } from "../../test-utils";
import { SyntaxHighlight } from "../../../backends/consts";

test("CodeEditor", async () => {
    const { asFragment } = render(
        <CodeEditor initialContent="foo" onChange={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("CodeEditor highlights HTML", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="<p>yay</p>"
            onChange={() => 0}
            language={SyntaxHighlight.XML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights YAML", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="foo: bar"
            onChange={() => 0}
            language={SyntaxHighlight.YAML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights JavaScript", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="alert(1);"
            onChange={() => 0}
            language={SyntaxHighlight.JAVASCRIPT}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights CSS", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="p { color: red; }"
            onChange={() => 0}
            language={SyntaxHighlight.CSS}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
