import * as React from "react";
import { useTranslation } from "react-i18next";
import { CommandBarToggle, EventlogToggle, OptionsToggle } from "./MenuToggle";
import Button from "../common/Button";
import DocsLink from "../common/DocsLink";
import HideInStatic from "../common/HideInStatic";
import * as modalActions from "../../ducks/ui/modal";
import { useAppDispatch } from "../../ducks";
import LanguageSelector from "./LanguageSelector";

OptionMenu.title = "Options";

export default function OptionMenu() {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    const openOptions = () => modalActions.setActiveModal("OptionModal");

    return (
        <div>
            <HideInStatic>
                <div className="menu-group">
                    <div className="menu-content">
                        <Button
                            title={t("header.optionMenu.openOptionsTitle")}
                            icon="fa-cogs text-primary"
                            onClick={() => dispatch(openOptions())}
                        >
                            {t("header.optionMenu.editOptions")} <sup>{t("header.optionMenu.alpha")}</sup>
                        </Button>
                    </div>
                    <div className="menu-legend">{t("header.optionMenu.optionsEditor")}</div>
                </div>

                <div className="menu-group">
                    <div className="menu-content">
                        <OptionsToggle name="anticache">
                            {t("header.optionMenu.stripCacheHeaders")}{" "}
                            <DocsLink resource="overview/features/#anticache" />
                        </OptionsToggle>
                        <OptionsToggle name="showhost">
                            {t("header.optionMenu.useHostHeader")}{" "}
                            <DocsLink resource="concepts/options/#showhost" />
                        </OptionsToggle>
                        <OptionsToggle name="ssl_insecure">
                            {t("header.optionMenu.dontVerifyServerCerts")}{" "}
                            <DocsLink resource="concepts/options/#ssl_insecure" />
                        </OptionsToggle>
                    </div>
                    <div className="menu-legend">{t("header.optionMenu.quickOptions")}</div>
                </div>
            </HideInStatic>

            <div className="menu-group">
                <div className="menu-content">
                    <EventlogToggle />
                    <CommandBarToggle />
                    <LanguageSelector />
                </div>
                <div className="menu-legend">{t("header.optionMenu.viewOptions")}</div>
            </div>
        </div>
    );
}
