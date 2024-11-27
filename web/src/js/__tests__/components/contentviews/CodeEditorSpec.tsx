jest.mock("../../../contrib/CodeMirror");
import * as React from "react";
import CodeEditor from "../../../components/contentviews/CodeEditor";
import { render } from "../../test-utils";

test("CodeEditor", async () => {
    const { asFragment } = render(<CodeEditor initialContent="foo" />);
    expect(asFragment()).toMatchSnapshot();
});
