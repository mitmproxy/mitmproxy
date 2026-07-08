import * as React from "react";
import { render } from "@testing-library/react";
import StatusBadge, { statusClass } from "../../../components/common/StatusBadge";

test.each([
    [101, "status-1xx"],
    [200, "status-2xx"],
    [204, "status-2xx"],
    [301, "status-3xx"],
    [404, "status-4xx"],
    [500, "status-5xx"],
    [599, "status-5xx"],
    [700, "status-other"],
    ["NOERROR", "status-other"],
])("statusClass(%s) === %s", (code, expected) => {
    expect(statusClass(code)).toBe(expected);
});

test("renders the code with the matching class", () => {
    const { container } = render(<StatusBadge code={404} />);
    const badge = container.querySelector(".status-badge");
    expect(badge?.textContent).toBe("404");
    expect(badge?.classList.contains("status-4xx")).toBe(true);
});
