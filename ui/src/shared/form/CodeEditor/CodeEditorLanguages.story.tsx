import React, { useState } from 'react';
import { CodeEditor } from './CodeEditor';

const markdownExample = `## Hello
Goodbye
`;

const javaScriptExample = `(function() {
  const bar = true;
})();`;

const pythonExample = `mytuple = ("apple", "banana", "cherry")
myit = iter(mytuple)

print(next(myit))
print(next(myit))
print(next(myit))`;

const yamlExample = `boolean: true
array:
  - string: 12
    enum: Mewtwo
    reference:
      reference:
        boolean: true
`;

const terraformExample = `terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region  = "us-west-2"
}

resource "aws_instance" "app_server" {
  ami           = "ami-830c94e3"
  instance_type = "t2.micro"

  tags = {
    Name = "ExampleAppServerInstance"
  }
}
`;

const jsonExample = JSON.stringify(
  {
    id: 'abc123',
    age: 28,
    balance: '$34.34',
    date: new Date('2020-05-01T12:00:00'),
    phone: '+3 (444) 444-4444',
    picture: 'foo/bar',
    active: false
  },
  null,
  2
);

export default {
  title: 'Form/Code Editor/Languages',
  component: CodeEditor
};

export const Json = () => {
  const [value, setValue] = useState<string>(jsonExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="json"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Markdown = () => {
  const [value, setValue] = useState<string>(markdownExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="markdown"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Javascript = () => {
  const [value, setValue] = useState<string>(javaScriptExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="javascript"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Python = () => {
  const [value, setValue] = useState<string>(pythonExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="python"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Terraform = () => {
  const [value, setValue] = useState<string>(terraformExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="hcl"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};

export const Yaml = () => {
  const [value, setValue] = useState<string>(yamlExample);

  return (
    <div style={{ width: '50vw', height: '300px' }}>
      <CodeEditor
        value={value}
        language="yaml"
        onChange={v => setValue(v as string)}
      />
    </div>
  );
};
