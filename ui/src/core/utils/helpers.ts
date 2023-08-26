import { SortingState } from '@tanstack/react-table';

const nestedFields = ['repo_name', 'file_path', 'template_type', 'provider'];

const getFieldKey = (name: string) => {
  if (nestedFields.includes(name)) {
    return `iambic_template.${name}`;
  }
  return name;
};

export const extractSortValue = (defaultValue, newValue?: SortingState) => {
  if (newValue?.length) {
    const value = newValue[0];
    const key = getFieldKey(value.id);
    return {
      sortingColumn: {
        id: 'id',
        sortingField: key,
        header: key,
        minWidth: 180
      },
      sortingDescending: value.desc
    };
  }
  return defaultValue;
};

export const getLinkFromResourceTemplate = resourceTemplate => {
  const strippedPath = resourceTemplate.file_path.replace(/\.yaml$/, '');
  // const provider = resourceTemplate.provider.toLowerCase();
  const repoName = resourceTemplate.repo_name.toLowerCase();
  return `/resources/iambic/${repoName}/${strippedPath}`;
};
