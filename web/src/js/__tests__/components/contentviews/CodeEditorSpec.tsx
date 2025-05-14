import * as React from "react";
import CodeEditor from "../../../components/contentviews/CodeEditor";
import { render } from "../../test-utils";

test("CodeEditor", async () => {
    const { asFragment } = render(
        <CodeEditor initialContent="foo" onChange={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("CodeEditor highlights JavaScript", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="alert(1);"
            onChange={() => 0}
            language="javascript"
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights HTML", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="<p>yay</p>"
            onChange={() => 0}
            language="html"
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights CSS", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="* { color: black; }"
            onChange={() => 0}
            language="css"
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights YAML", async () => {
    const { asFragment } = render(
        <CodeEditor
            initialContent="foo: bar"
            onChange={() => 0}
            language="yaml"
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
