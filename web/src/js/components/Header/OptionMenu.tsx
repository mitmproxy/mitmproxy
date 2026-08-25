import * as React from "react";
import { CommandBarToggle, EventlogToggle, OptionsToggle } from "./MenuToggle";
import Button from "../common/Button";
import DocsLink from "../common/DocsLink";
import HideInStatic from "../common/HideInStatic";
import * as modalActions from "../../ducks/ui/modal";
import * as optionsActions from "../../ducks/options";
import { useAppDispatch, useAppSelector } from "../../ducks";

OptionMenu.title = "Options";

function ThemeSelect() {
    const dispatch = useAppDispatch();
    const value = useAppSelector((state) => state.options.web_theme);
    const choices = useAppSelector(
        (state) => state.options_meta.web_theme?.choices,
    ) ?? ["system", "dark", "light"];

    return (
        <div className="menu-entry">
            <label>
                Theme
                <select
                    className="theme-select"
                    value={value}
                    onChange={(e) =>
                        dispatch(
                            optionsActions.update("web_theme", e.target.value),
                        )
                    }
                >
                    {choices.map((choice) => (
                        <option key={choice} value={choice}>
                            {choice}
                        </option>
                    ))}
                </select>
            </label>
        </div>
    );
}

export default function OptionMenu() {
    const dispatch = useAppDispatch();
    const openOptions = () => modalActions.setActiveModal("OptionModal");

    return (
        <div>
            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            title="Open Options"
                            icon="settings"
                            iconClassName="text-primary"
                            onClick={() => dispatch(openOptions())}
                        >
                            Edit Options
                        </Button>
                    </div>
                    <div className="menu-legend">Options Editor</div>
                </div>

                <div className="menu-group">
                    <div className="menu-content">
                        <OptionsToggle name="anticache">
                            Strip cache headers{" "}
                            <DocsLink resource="overview/features/#anticache" />
                        </OptionsToggle>
                        <OptionsToggle name="showhost">
                            Use host header for display{" "}
                            <DocsLink resource="concepts/options/#showhost" />
                        </OptionsToggle>
                        <OptionsToggle name="ssl_insecure">
                            Don&apos;t verify server certificates{" "}
                            <DocsLink resource="concepts/options/#ssl_insecure" />
                        </OptionsToggle>
                    </div>
                    <div className="menu-legend">Quick Options</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <EventlogToggle />
                    <CommandBarToggle />
                </div>
                <div className="menu-legend">View Options</div>
            </div>

            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <ThemeSelect />
                    </div>
                    <div className="menu-legend">Appearance</div>
                </div>
            </HideInStatic>
        </div>
    );
}
