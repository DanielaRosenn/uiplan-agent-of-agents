/* Minimal ESLint config for the UiPlan Studio app.
 * Run `npm install --save-dev eslint @typescript-eslint/parser
 *   @typescript-eslint/eslint-plugin eslint-plugin-react-hooks` once,
 * then `npm run lint`.
 */
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
    ecmaFeatures: { jsx: true },
  },
  plugins: ["@typescript-eslint", "react-hooks"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
  ],
  rules: {
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "off",
  },
  ignorePatterns: ["dist/", "node_modules/", "*.cjs"],
};
