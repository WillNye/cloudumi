import SectionHeader from './SectionHeader';

export default {
  title: 'Elements/SectionHeader',
  component: SectionHeader
};

export const Basic = () => {
  return (
    <div>
      <SectionHeader title="Small Header" size="small" />
      <p>Small header content goes here.</p>
      <SectionHeader title="Medium Header" subtitle="Subtitle" />
      <p>Medium header content goes here.</p>
      <SectionHeader title="Large Header" size="large" />
      <p>Large header content goes here.</p>
    </div>
  );
};
