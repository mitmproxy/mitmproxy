const versionRegex = /^\/(stable|archive\/v\d+)/;

async function fetchVersions() {
    const resp = await fetch("https://s3-us-west-2.amazonaws.com/docs.mitmproxy.org?delimiter=/&prefix=archive/")
        .then(response => response.text());
    const versions = resp
        .match(/(?<=<Prefix>archive\/v)\d+(?=\/<\/Prefix>)/g)
        .toSorted((a,b) => b - a)
        .map(x => `v${x}`)
    versions.unshift("dev", "stable");
    return versions;
}

class VersionSelector extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {
        const currentVersion = (
            versionRegex
                .exec(location.pathname)?.[1]
                .replace("archive/","")
            || "dev"
        );

        if (currentVersion === "dev") {
            this.innerHTML = `
                <select>
                    <option value="/dev" selected>dev</option>
                    <option value="/stable">stable</option>
                    <option disabled>...</option>
                </select>`;
        } else if (currentVersion === "stable") {
            this.innerHTML = `
                <select>
                    <option value="/dev">dev</option>
                    <option value="/stable" selected>stable</option>
                    <option disabled>...</option>
                </select>`;
        } else {
            this.innerHTML = `
                <select>
                    <option value="/dev">dev</option>
                    <option value="/stable" >stable</option>
                    <option selected>${currentVersion}</option>
                    <option disabled>...</option>
                </select>`;
        }

        const selectElement = this.querySelector('select');
        selectElement.addEventListener('focus', async () => {
            const versions = await fetchVersions();
            selectElement.innerHTML = '';
            versions.forEach(version => {
                const option = document.createElement('option');
                option.value = version.startsWith("v") ? `/archive/${version}` : `/${version}`;
                option.text = version;
                option.selected = currentVersion === version;
                selectElement.appendChild(option);
            });
        }, {once: true});
        selectElement.addEventListener('change', () => {
            window.location.pathname = selectElement.value + location.pathname.replace(versionRegex, "")
        });
    }
}

window.customElements.define('version-selector', VersionSelector);