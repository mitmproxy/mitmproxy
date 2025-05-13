process.env.TZ = "UTC";
const err = console.error;
console.warn = console.error = function () {
    err.apply(console, arguments);
    throw new Error(arguments[0]);
};
