import { SortingState } from '@tanstack/react-table';

export const extractSortValue = (defaultValue, newValue?: SortingState) => {
  if (newValue?.length) {
    const value = newValue[0];
    return {
      sortingColumn: {
        id: 'id',
        sortingField: value.id,
        header: value.id,
        minWidth: 180
      },
      sortingDescending: value.desc
    };
  }
  return defaultValue;
};
