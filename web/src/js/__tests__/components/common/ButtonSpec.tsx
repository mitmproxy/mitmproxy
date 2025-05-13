import * as React from "react";
import Button from "../../../components/common/Button";
import { render } from "../../test-utils";

describe("Button Component", () => {
    it("should render correctly", () => {
        const { asFragment } = render(
            <Button
                className="classname"
                onClick={() => "onclick"}
                title="title"
                icon="icon"
            >
                <a>foo</a>
            </Button>,
        );
        expect(asFragment()).toMatchSnapshot();
    });

    it("should be able to be disabled", () => {
        const { asFragment } = render(
            <Button className="classname" onClick={() => "onclick"} disabled>
                <a>foo</a>
            </Button>,
        );
        expect(asFragment()).toMatchSnapshot();
    });
});
