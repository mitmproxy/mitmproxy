process.env.TZ = 'UTC';
console.warn = console.error = (message) => { throw new Error(message) };
