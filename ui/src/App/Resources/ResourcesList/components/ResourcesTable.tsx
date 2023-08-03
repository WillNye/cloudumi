import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Table } from 'shared/elements/Table';
import { resourcesColumns } from './constants';
import { useQuery } from '@tanstack/react-query';
import { getAllResources } from 'core/API/resources';
import { extractSortValue } from 'core/utils/helpers';
import css from './ResourcesTable.module.css';

const defaultSortField = {
  sortingColumn: {
    id: 'id',
    sortingField: 'iambic_template.template_type',
    header: 'iambic_template.template_type',
    minWidth: 180
  },
  sortingDescending: false
};

const ResourcesTable = () => {
  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 30
    },
    sorting: extractSortValue(defaultSortField),
    filtering: {
      tokens: [],
      operation: 'and'
    }
  });

  const { isLoading, data: resourcesData } = useQuery({
    queryFn: getAllResources,
    queryKey: ['resources', query]
  });

  const tableRows = useMemo(() => {
    return (resourcesData?.data?.data || []).map(item => {
      const strippedPath = item.file_path.replace(/\.yaml$/, '');
      const provider = item.provider.toLowerCase();
      const repoName = item.repo_name.toLowerCase();
      return {
        ...item,
        file_path: (
          <Link to={`/resources/${provider}/${repoName}${strippedPath}`}>
            {item.file_path}
          </Link>
        )
      };
    });
  }, [resourcesData]);

  const handleOnPageChange = useCallback((newPageIndex: number) => {
    setQuery(query => ({
      ...query,
      pagination: {
        ...query.pagination,
        currentPageIndex: newPageIndex
      }
    }));
  }, []);

  const handleOnSort = useCallback(value => {
    const sortValue = extractSortValue(defaultSortField, value);
    setQuery(query => ({
      ...query,
      sorting: sortValue
    }));
  }, []);

  const handleOnFilterChange = useCallback(filter => {
    setQuery(query => ({
      ...query,
      filtering: filter,
      pagination: {
        ...query.pagination,
        currentPageIndex: 1
      }
    }));
  }, []);

  return (
    <>
      <div className={css.container}>
        <div className={css.filter}>
          <PropertyFilter
            expandToViewport
            onChange={({ detail }) => handleOnFilterChange(detail)}
            query={query.filtering as PropertyFilterProps.Query}
            i18nStrings={{
              filteringAriaLabel: 'your choice',
              dismissAriaLabel: 'Dismiss',
              filteringPlaceholder: 'Filter Resources',
              groupValuesText: 'Values',
              groupPropertiesText: 'Properties',
              operatorsText: 'Operators',
              operationAndText: 'and',
              operationOrText: 'or',
              operatorLessText: 'Less than',
              operatorLessOrEqualText: 'Less than or equal',
              operatorGreaterText: 'Greater than',
              operatorGreaterOrEqualText: 'Greater than or equal',
              operatorContainsText: 'Contains',
              operatorDoesNotContainText: 'Does not contain',
              operatorEqualsText: 'Equals',
              operatorDoesNotEqualText: 'Does not equal',
              editTokenHeader: 'Edit filter',
              propertyText: 'Property',
              operatorText: 'Operator',
              valueText: 'Value',
              cancelActionText: 'Cancel',
              applyActionText: 'Apply',
              allPropertiesLabel: 'All properties',
              tokenLimitShowMore: 'Show more',
              tokenLimitShowFewer: 'Show fewer',
              clearFiltersText: 'Clear filters',
              removeTokenButtonAriaLabel: token =>
                `Remove token ${token.propertyKey} ${token.operator} ${token.value}`,
              enteredTextLabel: text => `Use: "${text}"`
            }}
            filteringOptions={[]}
            filteringProperties={[
              {
                key: 'iambic_template.template_type',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Template Type',
                groupValuesLabel: 'Template Type values'
              },
              {
                key: 'resource_id',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Resource ID',
                groupValuesLabel: 'Resource ID values'
              },
              {
                key: 'iambic_template.repo_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Repository Name',
                groupValuesLabel: 'Repository Name values'
              },
              {
                key: 'iambic_template.file_path',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'File Path',
                groupValuesLabel: 'File Path values'
              }
            ]}
          />
        </div>
        <div className={css.table}>
          <Table
            columns={resourcesColumns}
            data={tableRows}
            border="row"
            isLoading={isLoading}
            totalCount={
              resourcesData?.data?.filtered_count || query.pagination.pageSize
            }
            pageSize={query.pagination.pageSize}
            pageIndex={query.pagination.currentPageIndex}
            handleOnPageChange={handleOnPageChange}
            handleOnSort={handleOnSort}
            showPagination
            enableSorting
          />
        </div>
      </div>
    </>
  );
};

export default ResourcesTable;
