import * as React from "react";
import { useTranslation } from "react-i18next";

export default React.memo(function LanguageSelector(): React.ReactElement {
    const { i18n, t } = useTranslation();

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const lang = e.target.value;
        i18n.changeLanguage(lang);
        localStorage.setItem("mitmweb-lang", lang);
    };

    return (
        <div className="menu-entry">
                <label htmlFor="language-selector">
                    {t("languageSelector.label")}
                </label>
                <select
                    id="language-selector"
                    className="language-selector form-control input-xs"
                    value={i18n.language}
                    onChange={handleChange}
                    title={t("languageSelector.label")}
                >
                    <option value="en">{t("languageSelector.english")}</option>
                    <option value="zh">{t("languageSelector.chinese")}</option>
                </select>
        </div>
    );
});
