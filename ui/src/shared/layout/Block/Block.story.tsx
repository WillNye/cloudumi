import React from 'react';
import { Input } from 'shared/form/Input';
import { Block } from './Block';

export default {
  title: 'Layout/Block',
  component: Block
};

export const Labelless = () => (
  <>
    <Block>
      Haxx0r ipsum else break headers private dereference bin race condition bit
      continue emacs public todo buffer ip mailbomb void strlen leapfrog.
    </Block>
    <Block>
      Haxx0r ipsum else break headers private dereference bin race condition bit
      continue emacs public todo buffer ip mailbomb void strlen leapfrog.
    </Block>
  </>
);

export const Inputs = () => (
  <>
    <Block label="Haxor">
      <Input />
    </Block>
  </>
);

export const Label = () => (
  <>
    <Block label="Haxor">
      Haxx0r ipsum else break headers private dereference bin race condition bit
      continue emacs public todo buffer ip mailbomb void strlen leapfrog.
    </Block>
    <Block label="Manifest">
      Haxx0r ipsum else break headers private dereference bin race condition bit
      continue emacs public todo buffer ip mailbomb void strlen leapfrog.
    </Block>
  </>
);

export const Required = () => (
  <Block label="Name" required={true}>
    Haxx0r ipsum else break headers private dereference.
  </Block>
);

export const Alignment = () => (
  <Block label="Name" required={true} alignment="end" direction="horizontal">
    Haxx0r ipsum else break headers private dereference.
  </Block>
);

export const Horizontal = () => (
  <Block label="Name" direction="horizontal" required={true}>
    Haxx0r ipsum else break headers private dereference.
  </Block>
);

export const HorizontalLarge = () => (
  <Block
    label="Name"
    direction="horizontal"
    required={true}
    style={{ maxWidth: 300 }}
  >
    Haxx0r ipsum else break headers private dereference bin race condition bit
    continue emacs public todo buffer ip mailbomb void strlen leapfrog. Haxx0r
    ipsum else break headers private dereference bin race condition bit continue
    emacs public todo buffer ip mailbomb void strlen leapfrog.
  </Block>
);
