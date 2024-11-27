import * as React from "react";
import { CommandBarToggle, EventlogToggle, OptionsToggle } from "./MenuToggle";
import Button from "../common/Button";
import DocsLink from "../common/DocsLink";
import HideInStatic from "../common/HideInStatic";
import * as modalActions from "../../ducks/ui/modal";
import { useAppDispatch } from "../../ducks";

OptionMenu.title = "Options";

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
                            icon="fa-cogs text-primary"
                            onClick={() => dispatch(openOptions())}
                        >
                            Edit Options <sup>alpha</sup>
                        </Button>
                    </div>
                    <div className="menu-legend">Options Editor</div>
                </div>

                <div className="menu-group">
                    <div className="menu-content">
                        <OptionsToggle name="anticache">
                            Strip cache headers{" "}
                            <DocsLink resource="overview-features/#anticache" />
                        </OptionsToggle>
                        <OptionsToggle name="showhost">
                            Use host header for display
                        </OptionsToggle>
                        <OptionsToggle name="ssl_insecure">
                            Don&apos;t verify server certificates
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
        </div>
    );
}
