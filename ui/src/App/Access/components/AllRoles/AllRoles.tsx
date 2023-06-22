import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { allRolesColumns } from '../EligibleRoles/constants';

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
      pageSize: 30
    },
    sorting: {
      sortingColumn: {
        id: 'id',
        sortingField: 'account_name',
        header: 'Account Name',
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
    return (allRolesData?.data || []).map(item => {
      const arn = item.arn.match(/\[(.+?)\]\((.+?)\)/)[1];
      return {
        ...item,
        // roleName: <Link to={`/resources/edit/${arn}`}>{arn}</Link>,
        roleName: <div>{arn}</div>,
        name: (
          <div>
            <div>{item.account_name}</div>
            <div className={css.tableSecondaryText}>{item.account_id}</div>
          </div>
        ),
        moreActions: <MoreActions role={item} />
      };
    });
  }, [allRolesData]);

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
                key: 'account_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Account Name',
                groupValuesLabel: 'Account Name values'
              },
              {
                key: 'account_id',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Account ID',
                groupValuesLabel: 'Account ID values'
              },
              {
                key: 'role_name',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'Role Name',
                groupValuesLabel: 'Role Name values'
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
          />
        </div>
      </div>
    </>
  );
};

export default AllRoles;
