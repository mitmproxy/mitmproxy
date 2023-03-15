import * as React from "react";
import FlowMenu from "../../../components/Header/FlowMenu";
import { render } from "../../test-utils";

test("FlowMenu", async () => {
    const { asFragment } = render(<FlowMenu />);
    expect(asFragment()).toMatchSnapshot();
});
