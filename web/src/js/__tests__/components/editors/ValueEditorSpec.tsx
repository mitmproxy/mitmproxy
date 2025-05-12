import * as React from "react";
import ValueEditor from "../../../components/editors/ValueEditor";
import { render, waitFor } from "../../test-utils";

test("ValueEditor", async () => {
    const onEditDone = jest.fn();
    const editor: { current?: ValueEditor | null } = {};
    const { asFragment } = render(
        <ValueEditor
            ref={(x) => {
                editor.current = x;
            }}
            content="hello world"
            onEditDone={onEditDone}
        />,
    );
    expect(asFragment()).toMatchSnapshot();

    if (!editor.current) throw "err";

    editor.current.startEditing();
    await waitFor(() => expect(editor.current?.isEditing()).toBeTruthy());

    editor.current.finishEditing();
    await waitFor(() => expect(onEditDone).toBeCalledWith("hello world"));
});
