const root = document.currentScript.src.split("/").slice(0, -1).join("/");

function escapeHTML(html) {
    return document.createElement('div').appendChild(document.createTextNode(html)).parentNode.innerHTML;
}

const originalContent = document.querySelector("main");
let currentContent = originalContent;

function setContent(innerHTML) {
    /* Replace the entire page contents. Calling this with an empty argument restores the original page. */
    let elem;
    if (innerHTML) {
        elem = document.createElement("main");
        elem.innerHTML = innerHTML;
    } else {
        elem = originalContent;
    }
    if (currentContent !== elem) {
        currentContent.replaceWith(elem);
        currentContent = elem;
    }
}

function getSearchTerm() {
    return (new URL(window.location)).searchParams.get("search");
}

/* the control flow here is: search input -> update location -> onInput */
const searchBox = document.querySelector("#search");
searchBox.addEventListener("input", function () {
    let url = new URL(window.location);
    if (searchBox.value.trim()) {
        url.hash = "";
        url.searchParams.set("search", searchBox.value);
    } else {
        url.searchParams.delete("search");
    }
    history.replaceState("", "", url.toString());
    onInput();
});
window.addEventListener("popstate", onInput);


let search, searchErr;


async function initialize() {
    /* Get the search index and compile it if necessary.
       This function will only be called once. */
    try {
        search = await new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.type = "text/javascript";
            script.async = true;
            script.onload = () => resolve(window.docsSearch);
            script.onerror = (e) => reject(e);
            script.src = root + "/searchindex.js";
            document.getElementsByTagName("head")[0].appendChild(script);
        });
    } catch (e) {
        searchErr = "Cannot fetch search index.";
    }
    onInput();
}

function onInput() {
    setContent((() => {
        const term = getSearchTerm();
        if (!term) {
            return null
        }
        if (searchErr) {
            return `<h3>Error: ${searchErr}</h3>`
        }
        if (!search) {
            return "<h3>Searching...</h3>"
        }

        window.scrollTo({top: 0, left: 0, behavior: 'auto'});

        const results = search(term);

        let html;
        if (results.length === 0) {
            html = `No search results for '${escapeHTML(term)}'.`
        } else {
            html = `<h4>${results.length} search result${results.length > 1 ? "s" : ""} for '${escapeHTML(term)}'.</h4>`;
        }
        for (let result of results) {
            let doc = result.doc;
            let url = `${root}${doc.url}`;
            html += `
                    <div class="search-result">
                    [${doc.section}] <a href="${url}">${doc.title}</a>
                    </div>
                `;

        }
        return html;
    })());
}

if (getSearchTerm()) {
    initialize();
    searchBox.value = getSearchTerm();
    onInput();
} else {
    searchBox.addEventListener("focus", initialize, {once: true});
}

/* keyboard navigation for results */
searchBox.addEventListener("keydown", e => {
    if (["ArrowDown", "ArrowUp", "Enter"].includes(e.key)) {
        let focused = currentContent.querySelector(".search-result.focused");
        if (!focused) {
            currentContent.querySelector(".search-result").classList.add("focused");
        } else if (
            e.key === "ArrowDown"
            && focused.nextElementSibling
            && focused.nextElementSibling.classList.contains("search-result")
        ) {
            focused.classList.remove("focused");
            focused.nextElementSibling.classList.add("focused");
            focused.nextElementSibling.scrollIntoView({
                behavior: "smooth",
                block: "nearest",
                inline: "nearest"
            });
        } else if (
            e.key === "ArrowUp"
            && focused.previousElementSibling
            && focused.previousElementSibling.classList.contains("search-result")
        ) {
            focused.classList.remove("focused");
            focused.previousElementSibling.classList.add("focused");
            focused.previousElementSibling.scrollIntoView({
                behavior: "smooth",
                block: "nearest",
                inline: "nearest"
            });
        } else if (
            e.key === "Enter"
        ) {
            focused.querySelector("a").click();
        }
    }
});
