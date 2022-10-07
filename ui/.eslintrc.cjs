// eslint-disable-next-line no-undef
module.exports = {
  "env": {
    "browser": true,
    "es2021": true
  },
  "extends": [
    "prettier",
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "overrides": [
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "ecmaVersion": "latest",
    "sourceType": "module"
  },
  "plugins": [
    "react",
    "@typescript-eslint"
  ],
  "rules": {
    "curly": 2,
    "react/react-in-jsx-scope": "off",
    "import/no-anonymous-default-export": [
      0
    ],
    "react/jsx-no-target-blank": [
      0
    ],
    "@typescript-eslint/no-explicit-any": "off"
  }
};
