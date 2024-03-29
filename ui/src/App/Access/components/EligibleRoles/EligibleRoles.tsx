import { PropertyFilter, PropertyFilterProps } from '@noqdev/cloudscape';
import { useCallback, useEffect, useMemo, useState } from 'react';
import RoleCredentialSummary from '../common/RoleCredentialSummary';

import MoreActions from '../common/MoreActions';
import { Table } from 'shared/elements/Table';
import { eligibleRolesColumns } from '../../constants';

import { ROLE_PROPERTY_SEARCH_FILTER } from 'App/Access/constants';
import AWSSignIn from '../common/AWSSignIn';
import { Notification, NotificationType } from 'shared/elements/Notification';
import css from './EligibleRoles.module.css';
import { useQuery } from '@tanstack/react-query';
import { getEligibleRoles } from 'core/API/roles';
import { LineBreak } from 'shared/elements/LineBreak';
import { getSearchParams, parseRoleEnvVariable } from './utils';

const EligibleRoles = () => {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filter, setFilter] = useState<PropertyFilterProps.Query>({
    tokens: [...getSearchParams()],
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

  const { isLoading, data: eligibleRolesData } = useQuery({
    queryFn: getEligibleRoles,
    queryKey: ['eligibleRoles', query]
  });

  useEffect(() => {
    setQuery(existingQuery => ({
      ...existingQuery,
      filtering: filter,
      pagination: {
        ...existingQuery.pagination,
        currentPageIndex: 1
      }
    }));
  }, [filter]);

  const handleOnPageChange = useCallback((newPageIndex: number) => {
    setQuery(query => ({
      ...query,
      pagination: {
        ...query.pagination,
        currentPageIndex: newPageIndex
      }
    }));
  }, []);

  const tableRows = useMemo(() => {
    return (eligibleRolesData?.data || []).map(item => {
      const roleName = item.role_name.match(/\[(.+?)\]\((.+?)\)/)[1];
      return {
        ...item,
        // roleName: <Link to={`/resources/edit/${item.arn}`}>{roleName}</Link>,
        roleName: <div>{roleName}</div>,
        name: (
          <div>
            <div>{item.account_name}</div>
            <div className={css.tableSecondaryText}>{item.account_id}</div>
          </div>
        ),
        arn: <AWSSignIn role={item} setErrorMessage={setErrorMessage} />,
        viewDetails: (
          <RoleCredentialSummary
            arn={item.arn}
            accountName={parseRoleEnvVariable(item.account_name)}
            roleName={roleName}
          />
        ),
        moreActions: <MoreActions role={item} />
      };
    });
  }, [eligibleRolesData]);

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
              },
              {
                key: 'arn',
                operators: ['=', '!=', ':', '!:'],
                propertyLabel: 'ARN',
                groupValuesLabel: 'ARN values'
              }
            ]}
          />
        </div>
        {errorMessage && (
          <>
            <Notification
              type={NotificationType.ERROR}
              header={errorMessage}
              fullWidth
              onClose={() => setErrorMessage(null)}
            />
            <LineBreak />
          </>
        )}
        <div className={css.table}>
          <Table
            data={tableRows}
            columns={eligibleRolesColumns}
            border="row"
            isLoading={isLoading}
            totalCount={
              eligibleRolesData?.filteredCount || query.pagination.pageSize
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

export default EligibleRoles;
