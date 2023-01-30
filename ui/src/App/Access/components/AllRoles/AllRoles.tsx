import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { Fragment, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { allRolesColumns } from '../EligibleRoles/constants';

import { ROLE_PROPERTY_SEARCH_FILTER } from 'App/Access/constants';
import css from './AllRoles.module.css';

const AllRoles = ({ data, getData, isLoading }) => {
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

  useEffect(
    function onQueryUpdate() {
      getData(query);
    },
    [query, getData]
  );

  useEffect(() => {
    setQuery(exstingQuery => ({
      ...exstingQuery,
      filtering: filter
    }));
  }, [filter]);

  const tableRows = useMemo(() => {
    return data.map(item => {
      const arn = item.arn.match(/\[(.+?)\]\((.+?)\)/)[1];
      const roleName = arn.split(':role').pop();
      return {
        ...item,
        roleName: <Link to={`/resources/edit/${arn}`}>{arn}</Link>,
        name: (
          <div>
            <div>{item.account_name}</div>
            <div className={css.tableSecondaryText}>{item.account_id}</div>
          </div>
        ),
        moreActions: <MoreActions />
      };
    });
  }, [data]);

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
            countText="5 matches"
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
