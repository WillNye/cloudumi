import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { allRolesColumns } from '../../constants';

import { IAMBIC_ROLE_PROPERTY_SEARCH_FILTER } from 'App/Access/constants';
import css from './AllRoles.module.css';
import { useQuery } from '@tanstack/react-query';
import { getAllRoles } from 'core/API/roles';
import { extractSortValue } from 'core/utils/helpers';

const defaultSortField = {
  sortingColumn: {
    id: 'id',
    sortingField: 'iambic_template.template_type',
    header: 'iambic_template.template_type',
    minWidth: 180
  },
  sortingDescending: false
};

const AllRoles = () => {
  const [filter, setFilter] = useState<PropertyFilterProps.Query>({
    tokens: [],
    operation: 'and'
  });

  const [query, setQuery] = useState({
    pagination: {
      currentPageIndex: 1,
      pageSize: 15
    },
    sorting: extractSortValue(defaultSortField),
    filtering: filter
  });

  const { isLoading, data: allRolesData } = useQuery({
    queryFn: getAllRoles,
    queryKey: ['allRoles', query]
  });

  useEffect(() => {
    setQuery(exstingQuery => ({
      ...exstingQuery,
      filtering: filter,
      pagination: {
        ...exstingQuery.pagination,
        currentPageIndex: 1
      }
    }));
  }, [filter]);

  const tableRows = useMemo(() => {
    return (allRolesData?.data?.data || []).map(item => {
      const strippedPath = item.file_path.replace(/\.yaml$/, '');
      const repoName = item.repo_name.toLowerCase();
      return {
        ...item,
        file_path: (
          <Link to={`/resources/iambic/${repoName}/${strippedPath}`}>
            {item.file_path}
          </Link>
        )
      };
    });
  }, [allRolesData]);

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
              filteringPlaceholder: IAMBIC_ROLE_PROPERTY_SEARCH_FILTER,
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
                key: 'secondary_resource_id',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Resource ARN',
                groupValuesLabel: 'Resource ARN values'
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
            data={tableRows}
            columns={allRolesColumns}
            border="row"
            isLoading={isLoading}
            totalCount={
              allRolesData?.data?.filtered_count || query.pagination.pageSize
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

export default AllRoles;
