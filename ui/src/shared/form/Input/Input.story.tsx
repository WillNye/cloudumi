import React, { useState } from 'react';
import { Input } from './Input';

export default {
  title: 'Form/Input',
  component: Input
};

export const Basic = () => <Input />;
export const Placeholder = () => <Input placeholder="Hello" />;
export const DefaultValue = () => <Input defaultValue="Hello" />;

export const Disabled = () => <Input defaultValue="Hello" disabled />;

export const Prefix = () => (
  <Input defaultValue="Hello" prefix="Name it something good!" />
);

export const Suffix = () => (
  <Input defaultValue="Hello" suffix="Name it something good!" />
);

export const PrefixAndSuffix = () => (
  <Input defaultValue="Hello" prefix={'$'} suffix={'.00'} />
);

export const FullWidth = () => (
  <div style={{ width: '300px' }}>
    <Input value="Hello" fullWidth={true} />
  </div>
);
