/* This currently is only used for jest. We use esbuild for actual bundling. */
module.exports = {
    presets: [
        '@babel/preset-react',
        ['@babel/preset-env', {targets: {node: "current"}}],
        '@babel/preset-typescript'
    ],
};
