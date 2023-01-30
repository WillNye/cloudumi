import { CodeBlock } from './CodeBlock';

export default {
  title: 'Elements/CodeBlock',
  component: CodeBlock
};

export const Basic = () => (
  <CodeBlock>
    {`const greeting = "Hello, World!";
console.log(greeting);
console.log("Hello, Again!");`}
  </CodeBlock>
);
