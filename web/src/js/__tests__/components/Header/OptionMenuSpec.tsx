import * as React from "react";
import OptionMenu from "../../../components/Header/OptionMenu";
import { render } from "../../test-utils";

describe("OptionMenu Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(<OptionMenu />);
        expect(asFragment()).toMatchSnapshot();
    });
});
