import * as React from "react";
import FileChooser from "../../../components/common/FileChooser";
import { render } from "@testing-library/react";

test("FileChooser", async () => {
    const { asFragment } = render(
        <FileChooser icon="play" text="open" onOpenFile={() => 0} />,
    );

    expect(asFragment()).toMatchSnapshot();
});
