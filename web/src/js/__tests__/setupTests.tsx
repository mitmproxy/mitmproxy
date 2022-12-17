import crypto from 'crypto'

Object.defineProperty(global, 'crypto', {
    value: {
        getRandomValues: (arr:any) => crypto.randomBytes(arr.length)
    }
});

Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(), 
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
    }))
});

Object.defineProperty(global, 'SVGStyleElement', {
    value: jest.fn().mockImplementation(() => ({}))
});