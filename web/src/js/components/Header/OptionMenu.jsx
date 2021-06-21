import React from "react"
import { connect } from "react-redux"
import { EventlogToggle, OptionsToggle } from "./MenuToggle"
import Button from "../common/Button"
import DocsLink from "../common/DocsLink"
import HideInStaticx from "../common/HideInStatic";
import * as modalActions from "../../ducks/ui/modal"

OptionMenu.title = 'Options'

function OptionMenu({ openOptions }) {
    return (
        <div>
            <HideInStaticx>
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
                        <OptionsToggle name="anticache">
                            Strip cache headers <DocsLink resource="overview-features/#anticache"/>
                        </OptionsToggle>
                        <OptionsToggle name="showhost">
                            Use host header for display
                        </OptionsToggle>
                        <OptionsToggle name="ssl_insecure">
                            Don't verify server certificates
                        </OptionsToggle>
                    </div>
                    <div className="menu-legend">Quick Options</div>
                </div>
            </HideInStaticx>

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
