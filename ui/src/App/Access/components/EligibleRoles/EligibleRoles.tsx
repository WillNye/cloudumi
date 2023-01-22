import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import RoleCredentialSummary from '../common/RoleCredentialSummary';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { eligibleRolesColumns } from './constants';
import { Button } from 'shared/elements/Button';

import css from './EligibleRoles.module.css';
import id from 'date-fns/esm/locale/id/index.js';

const EligibleRoles = ({ data, getData, isLoading }) => {
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

  useEffect(function onMount() {
    getData(query);
  }, []);

  // Fetch new data when query changes
  useEffect(() => {
    getData(query);
  }, [query]);

  useEffect(() => {
    setQuery({
      ...query,
      filtering: filter
    });
  }, [filter]);

  const tableRows = useMemo(() => {
    return data.map(item => {
      return {
        ...item,
        roleName: (
          <Link to={`/resources/edit/${item.arn}`}>
            {item.role_name.match(/\[(.+?)\]\((.+?)\)/)[1]}
          </Link>
        ),
        name: (
          <div>
            <div>{item.account_name}</div>
            <div className={css.tableSecondaryText}>{item.account_id}</div>
          </div>
        ),
        arn: (
          <Button
            fullWidth
            color={item.inactive_tra ? 'secondary' : 'primary'}
            size="small"
          >
            {item.inactive_tra ? 'Request Temporary Access' : 'Signin'}
          </Button>
        ),
        viewDetails: <RoleCredentialSummary />,
        moreActions: <MoreActions />
      };
    });
  }, [data]);

  return (
    <>
      <div className={css.container}>
        <div className={css.filter}>
          <PropertyFilter
            // expandToViewport
            onChange={({ detail }) => setFilter(detail)}
            query={filter}
            i18nStrings={{
              filteringAriaLabel: 'your choice',
              dismissAriaLabel: 'Dismiss',
              filteringPlaceholder:
                'Filter distributions by text, property or value',
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
            columns={eligibleRolesColumns}
            border="row"
            isLoading={isLoading}
          />
        </div>
      </div>
    </>
  );
};

export default EligibleRoles;
