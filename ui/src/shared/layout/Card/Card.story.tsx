import React from 'react';
import { Card } from './Card';

export default {
  title: 'Layout/Card',
  component: Card
};

export const Basic = () => <Card>Basic card</Card>;
export const Colors = () => (
  <>
    <Card>Basic card</Card>
    <Card color="danger" variant="outlined">
      Basic card
    </Card>
    <Card color="primary">Basic card</Card>
    <Card color="secondary">Basic card</Card>
    <Card color="warning">Basic card</Card>
  </>
);

export const NoPadding = () => <Card disablePadding>No padding card</Card>;

export const Header = () => (
  <Card variant="outlined" header="Pro Tip">
    Headers are headers
  </Card>
);
