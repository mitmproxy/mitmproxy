const err = console.error;
console.warn = console.error = function () {
    err.apply(console, arguments);
    throw new Error(arguments[0]);
};

// jsdom does not implement matchMedia; provide a light-theme stub.
if (typeof window.matchMedia !== "function") {
    window.matchMedia = (query) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
    });
}
