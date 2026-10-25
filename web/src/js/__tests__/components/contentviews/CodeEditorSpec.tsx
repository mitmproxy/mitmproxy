import * as React from "react";
import CodeEditor from "../../../components/contentviews/CodeEditor";
import { fireEvent, render } from "../../test-utils";
import { SyntaxHighlight } from "../../../backends/consts";

test("CodeEditor", async () => {
    const { asFragment } = render(
        <CodeEditor content="foo" onChange={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("CodeEditor highlights HTML", async () => {
    const { asFragment } = render(
        <CodeEditor
            content="<p>yay</p>"
            onChange={() => 0}
            language={SyntaxHighlight.XML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights YAML", async () => {
    const { asFragment } = render(
        <CodeEditor
            content="foo: bar"
            onChange={() => 0}
            language={SyntaxHighlight.YAML}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights JavaScript", async () => {
    const { asFragment } = render(
        <CodeEditor
            content="alert(1);"
            onChange={() => 0}
            language={SyntaxHighlight.JAVASCRIPT}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});
test("CodeEditor highlights CSS", async () => {
    const { asFragment } = render(
        <CodeEditor
            content="p { color: red; }"
            onChange={() => 0}
            language={SyntaxHighlight.CSS}
        />,
    );
    expect(asFragment()).toMatchSnapshot();
});

test("CodeEditor renders content in read-only usage without an onChange", async () => {
    const { container } = render(
        <CodeEditor content="readonly body" readonly />,
    );
    expect(container.querySelector(".cm-content")?.textContent).toContain(
        "readonly body",
    );
});

test("CodeEditor triggers onSave on Ctrl/Cmd+S when focused", async () => {
    const onSave = jest.fn();
    const { container } = render(
        <CodeEditor content="foo" onChange={() => 0} onSave={onSave} />,
    );

    const content = container.querySelector(".cm-content") as HTMLElement;
    content.focus();
    fireEvent.keyDown(content, { key: "s", ctrlKey: true });

    expect(onSave).toHaveBeenCalledTimes(1);
});
