import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { Table } from 'shared/elements/Table';
import { resourcesColumns } from './constants';
import css from './ResourcesTable.module.css';
import { useQuery } from '@tanstack/react-query';
import { getAllResources } from 'core/API/settings';
// import { Resource } from './types';

const ResourcesTable = () => {
  const [filter, setFilter] = useState<PropertyFilterProps.Query>({
    tokens: [],
    operation: 'and'
  });

  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 30
    },
    sorting: {
      sortingColumn: {
        id: 'id',
        sortingField: 'template_type',
        header: 'template_type',
        minWidth: 180
      },
      sortingDescending: false
    },
    filtering: filter
  });

  const { isLoading, data: resourcesData } = useQuery({
    queryFn: getAllResources,
    queryKey: ['resources', query]
  });

  useEffect(() => {
    setQuery(existingQuery => ({
      ...existingQuery,
      filtering: filter
    }));
  }, [filter]);

  const tableRows = useMemo(() => {
    return (resourcesData?.data || []).map(item => {
      const resourceId = item.id;
      return {
        ...item,
        name: <Link to={`/resources/edit/${resourceId}`}>{item.name}</Link>
      };
    });
  }, [resourcesData]);

  const handleOnPageChange = (newPageIndex: number) => {
    setQuery(query => ({
      ...query,
      pagination: {
        ...query.pagination,
        currentPageIndex: newPageIndex
      }
    }));
  };

  return (
    <>
      <div className={css.container}>
        <div className={css.filter}>
          <PropertyFilter
            expandToViewport
            onChange={({ detail }) => setFilter(detail)}
            query={filter}
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
            countText="5 matches"
            filteringOptions={[]}
            filteringProperties={[
              {
                key: 'template_type',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Template Type',
                groupValuesLabel: 'Template Type values'
              },
              {
                key: 'identifier',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Identifier',
                groupValuesLabel: 'Identifier values'
              },
              {
                key: 'repository_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Repository Name',
                groupValuesLabel: 'Repository Name values'
              },
              {
                key: 'file_path',
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
            showPagination
            totalCount={
              resourcesData?.filtered_count || query.pagination.pageSize
            }
            pageSize={query.pagination.pageSize}
            pageIndex={query.pagination.currentPageIndex}
            handleOnPageChange={handleOnPageChange}
          />
        </div>
      </div>
    </>
  );
};

export default ResourcesTable;
