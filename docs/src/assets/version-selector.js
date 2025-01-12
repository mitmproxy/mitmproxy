class VersionSelector extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const version = this.getAttribute("version") || (
            location.pathname.startsWith("/stable/") ?
                "stable" : "dev"
        );
        this.innerHTML = `
        Version: ${version}
            <!--<select readonly="">
                <option>${version}</option>
                <option>Loading...</option>
            </select>-->
        `;
    }
}

window.customElements.define('version-selector', VersionSelector);