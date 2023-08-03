import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { allRolesColumns } from '../../constants';

import { ROLE_PROPERTY_SEARCH_FILTER } from 'App/Access/constants';
import css from './AllRoles.module.css';
import { useQuery } from '@tanstack/react-query';
import { getAllRoles } from 'core/API/roles';

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
    sorting: {
      sortingColumn: {
        id: 'id',
        sortingField: 'iambic_template.template_type',
        header: 'iambic_template.template_type',
        minWidth: 180
      },
      sortingDescending: false
    },
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
      const provider = item.provider.toLowerCase();
      const repoName = item.repo_name.toLowerCase();
      return {
        ...item,
        file_path: (
          <Link to={`/resources/${provider}/${repoName}${strippedPath}`}>
            {item.file_path}
          </Link>
        ),
        moreActions: <MoreActions role={item} />
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
              filteringPlaceholder: ROLE_PROPERTY_SEARCH_FILTER,
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
            showPagination
          />
        </div>
      </div>
    </>
  );
};

export default AllRoles;
