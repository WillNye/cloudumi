// eslint-disable-next-line no-undef
module.exports = {
  env: {
    browser: true,
    es2021: true,
    jest: true
  },
  extends: [
    'prettier',
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:@typescript-eslint/recommended'
  ],
  overrides: [],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  settings: {
    react: {
      version: 'detect'
    },
    'import/resolver': {
      node: {
        extensions: ['.js', '.jsx', '.ts', '.tsx'],
        moduleDirectory: ['node_modules', 'src/']
      }
    }
  },
  plugins: ['react', '@typescript-eslint'],
  rules: {
    curly: 2,
    'no-unused-vars': [
      'off',
      {
        argsIgnorePattern: '^_',
        ignoreRestSiblings: true,
        args: 'none'
      }
    ],
    'react/prop-types': ['off'],
    'react/display-name': ['off'],
    '@typescript-eslint/ban-ts-comment': ['warn'],
    'no-debugger': ['warn'],
    'react/react-in-jsx-scope': 'off',
    'import/no-anonymous-default-export': [0],
    'react/jsx-no-target-blank': [0],
    '@typescript-eslint/no-explicit-any': 'off',
    'no-multiple-empty-lines': [2, { max: 1 }],
    'max-len': [
      2,
      {
        code: 120,
        tabWidth: 2,
        ignoreUrls: true
      }
    ],
    'max-params': ['error', 3],
    complexity: ['error', 12],
    'no-multi-spaces': 0,
    'import-order/import-order': 0,
    'operator-linebreak': 0,
    'no-useless-escape': 0,
    'no-labels': 'error',
    'no-nested-ternary': 0,
    'prefer-const': 0,
    'eol-last': 0,
    'no-duplicate-imports': 0
  },
  ignorePatterns: ['!.storybook']
};
