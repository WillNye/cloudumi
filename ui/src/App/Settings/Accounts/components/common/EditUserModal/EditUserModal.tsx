import { FC, Fragment, useCallback, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Icon } from 'shared/elements/Icon';
import { Input } from 'shared/form/Input';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import {
  createGroupMemberships,
  getAllGroups,
  updateUser
} from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { User } from '../../../types';
import { UPDATE_USER_ACTIONS } from '../../../constants';
import { Search } from 'shared/form/Search';
import { Chip } from 'reablocks';
import { Divider } from 'shared/elements/Divider';
import { useMutation } from '@tanstack/react-query';
import styles from './EditUserModal.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import classNames from 'classnames';

type UpdateUserParams = {
  data: { id: string; email?: string; username?: string };
  action: UPDATE_USER_ACTIONS;
};

type CreateUserGroupsParams = {
  users: string[];
  groups: string[];
  check_deleted?: boolean;
};

type EditUserModalProps = {
  canEdit: boolean;
  user: User;
};

const updatingUserSchema = Yup.object().shape({
  email: Yup.string().email().required('Required'),
  username: Yup.string().required('Required')
});

// eslint-disable-next-line complexity
const EditUserModal: FC<EditUserModalProps> = ({ canEdit, user }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [userGroups, setUserGroups] = useState(user.groups);
  const [isSearching, setIsSearching] = useState(false);
  const [isUpdatingGroups, setIsUpdatingGroups] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchValue, setSearchValue] = useState('');

  const { mutateAsync: updateUserMutation } = useMutation({
    mutationFn: (userData: UpdateUserParams) =>
      updateUser(userData.data, userData.action)
  });

  const { mutateAsync: createUserGroupsMutation } = useMutation({
    mutationFn: (data: CreateUserGroupsParams) =>
      createGroupMemberships({ ...data, check_deleted: true })
  });

  const { mutateAsync: searchMutation } = useMutation({
    mutationFn: (search: string) => {
      const query = {
        filter: {
          pagination: { currentPageIndex: 1, pageSize: 10 },
          filtering: {
            tokens: [{ propertyKey: 'name', operator: ':', value: search }],
            operation: 'and'
          }
        }
      };
      return getAllGroups({ queryKey: ['userGroups', query] });
    }
  });

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(updatingUserSchema),
    defaultValues: {
      email: user.email,
      username: user.username
    }
  });

  const NOT_MANUAL = user.managed_by != 'MANUAL';

  const resultRenderer = result => <p>{result.name}</p>;
  const onSelectResult = group => {
    setSearchValue(group.name);
    setUserGroups(groups => [...new Set([...groups, group.name])]);
  };

  const reseActions = useCallback(() => {
    setErrorMessage(null);
    setSuccessMessage(null);
  }, []);

  const resetUserCredentials = useCallback(
    async (action: UPDATE_USER_ACTIONS) => {
      reseActions();
      setIsLoading(true);
      try {
        await updateUserMutation({
          data: {
            id: user.id
          },
          action
        });
        setSuccessMessage('Successfully updated user credentials');
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while resetting user credentials'
        );
      }
      setIsLoading(false);
    },
    [user.id, reseActions, updateUserMutation]
  );

  const onSubmit = useCallback(
    async ({ email, username }) => {
      reseActions();
      try {
        await updateUserMutation({
          data: {
            id: user.id,
            email,
            username
          },
          action: UPDATE_USER_ACTIONS.UPDATE_USER
        });
        setSuccessMessage('Successfully updated user');
        // TODO refetch all users
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while updating new user'
        );
      }
    },
    [user.id, reseActions, updateUserMutation]
  );

  const handleSearch = useCallback(
    async e => {
      const value = e.target.value;
      setSearchValue(value);

      if (!value) {
        setSearchResults([]);
        return;
      }
      setIsSearching(true);
      try {
        const res = await searchMutation(value);
        setSearchResults(res.data.data);
      } catch (error) {
        // TODO: Properly handle error
        console.error(error);
      }
      setIsSearching(false);
    },
    [searchMutation]
  );

  const updateGroupMemberships = useCallback(async () => {
    reseActions();
    setIsUpdatingGroups(true);
    try {
      await createUserGroupsMutation({
        users: [user.email],
        groups: userGroups
      });
      // TODO: update user groups
      setSuccessMessage('Successfully updated user groups');
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while updating user groups'
      );
    }
    setIsUpdatingGroups(false);
  }, [user.email, userGroups, reseActions, createUserGroupsMutation]);

  const handleDeleteChip = index => {
    setUserGroups([...new Set([...userGroups.filter((ug, i) => i != index)])]);
  };

  if (!canEdit) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <div className={styles.btn} onClick={() => setShowDialog(true)}>
        <Icon name="edit" size="medium" />
      </div>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Edit User Details"
        size="medium"
      >
        <div className={styles.content}>
          {errorMessage && (
            <Notification
              type={NotificationType.ERROR}
              header={errorMessage}
              showCloseIcon={false}
              fullWidth
            />
          )}
          {successMessage && (
            <Notification
              type={NotificationType.SUCCESS}
              header={successMessage}
              showCloseIcon={false}
              fullWidth
            />
          )}
          <LineBreak size="small" />
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block disableLabelPadding label="Username" required></Block>
            <Input
              fullWidth
              placeholder="username"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('username', {
                disabled: user?.managed_by != 'MANUAL'
              })}
            />
            {errors?.username && touchedFields.username && (
              <p>{errors.username.message}</p>
            )}
            <LineBreak />
            <Block disableLabelPadding label="Email" required></Block>
            <Input
              fullWidth
              placeholder="email"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('email', { disabled: user?.managed_by != 'MANUAL' })}
            />
            {errors?.email && touchedFields.email && (
              <p>{errors.email.message}</p>
            )}
            <LineBreak />
            <Button
              size="small"
              type="submit"
              disabled={isSubmitting || !isValid || isLoading || NOT_MANUAL}
              fullWidth
            >
              {isSubmitting ? 'Updating User...' : 'Update User'}
            </Button>
          </form>
          <LineBreak />
          <div className={styles.userGroups}>
            {!NOT_MANUAL && (
              <>
                <Block disableLabelPadding label="Add Groups" required></Block>
                <Search
                  fullWidth
                  resultRenderer={resultRenderer}
                  results={searchResults}
                  onChange={handleSearch}
                  value={searchValue}
                  onResultSelect={onSelectResult}
                  isLoading={isSearching}
                />
              </>
            )}
            <div className={styles.groups}>
              <h5>User Groups</h5>
              <Divider />
              {userGroups.length ? (
                <div>
                  {userGroups.map((group, index) => (
                    <Chip className={styles.group} key={index}>
                      {group}
                      {!NOT_MANUAL && (
                        <>
                          {' '}
                          <Icon
                            name="close"
                            size="small"
                            onClick={() => handleDeleteChip(index)}
                          />
                        </>
                      )}
                    </Chip>
                  ))}
                </div>
              ) : (
                <p>No Groups Available for this User</p>
              )}
            </div>
            <Button
              disabled={isUpdatingGroups || NOT_MANUAL}
              size="small"
              fullWidth
              onClick={updateGroupMemberships}
            >
              Update Group Memberships
            </Button>
          </div>
          <LineBreak />
          <div
            className={classNames(
              {
                [styles.hidden]: NOT_MANUAL
              },
              styles.actions
            )}
          >
            <Button
              color="secondary"
              variant="outline"
              size="small"
              disabled={isLoading}
              onClick={() =>
                resetUserCredentials(UPDATE_USER_ACTIONS.RESET_PASSWORD)
              }
              fullWidth
            >
              Reset Password
            </Button>
            <Divider orientation="vertical" />
            <Button
              color="secondary"
              variant="outline"
              size="small"
              disabled={isLoading}
              onClick={() =>
                resetUserCredentials(UPDATE_USER_ACTIONS.RESET_MFA)
              }
              fullWidth
            >
              Reset MFA
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default EditUserModal;
