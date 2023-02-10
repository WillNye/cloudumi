import { Search } from './Search';

export default {
  title: 'Form/Search',
  component: Search
};

export const Basic = () => {
  return (
    <Search
      onSearch={() => {
        //
      }}
    />
  );
};
