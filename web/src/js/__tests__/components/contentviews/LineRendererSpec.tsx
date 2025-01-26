import * as React from "react";
import LineRenderer from "../../../components/contentviews/LineRenderer";
import { fireEvent, render, screen } from "../../test-utils";

test("LineRenderer", async () => {
    const lines: [style: string, text: string][][] = [
        [
            ["header", "foo: "],
            ["text", "42"],
        ],
        [
            ["header", "bar: "],
            ["text", "43"],
        ],
    ];

    const showMore = jest.fn();
    const { asFragment } = render(
        <LineRenderer lines={lines} maxLines={1} showMore={showMore} />,
    );
    expect(asFragment()).toMatchSnapshot();
    fireEvent.click(screen.getByText("Show more"));
    expect(showMore).toBeCalled();
});

test("No lines", async () => {
    const { asFragment } = render(
        <LineRenderer lines={[]} maxLines={1} showMore={() => 0} />,
    );
    expect(asFragment()).toMatchSnapshot();
});
