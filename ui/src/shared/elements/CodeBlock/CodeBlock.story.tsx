import { CodeBlock } from './CodeBlock';

export default {
  title: 'Elements/CodeBlock',
  component: CodeBlock
};

export const Basic = () => (
  <CodeBlock
    code={`const greeting = "Hello, World!";
console.log(greeting);
console.log("Hello, Again!");`}
  />
);
