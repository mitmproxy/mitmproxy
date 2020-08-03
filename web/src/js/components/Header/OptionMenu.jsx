import React from "react"
import { connect } from "react-redux"
import { EventlogToggle, SettingsToggle } from "./MenuToggle"
import Button from "../common/Button"
import DocsLink from "../common/DocsLink"
import HideInStatic from "../common/HideInStatic";
import * as modalActions from "../../ducks/ui/modal"

OptionMenu.title = 'Options'

function OptionMenu({ openOptions }) {
    return (
        <div>
            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button title="Open Options" icon="fa-cogs text-primary"
                                onClick={openOptions}>
                            Edit Options <sup>alpha</sup>
                        </Button>
                    </div>
                    <div className="menu-legend">Options Editor</div>
                </div>

                <div className="menu-group">
                    <div className="menu-content">
                        <SettingsToggle setting="anticache">
                            Strip cache headers <DocsLink resource="overview-features/#anticache"/>
                        </SettingsToggle>
                        <SettingsToggle setting="showhost">
                            Use host header for display
                        </SettingsToggle>
                        <SettingsToggle setting="ssl_insecure">
                            Don't verify server certificates
                        </SettingsToggle>
                    </div>
                    <div className="menu-legend">Quick Options</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <EventlogToggle/>
                </div>
                <div className="menu-legend">View Options</div>
            </div>
        </div>
    )
}

export default connect(
    null,
    {
        openOptions: () => modalActions.setActiveModal('OptionModal')
    }
)(OptionMenu)
