import { FC, Fragment, useCallback, useState } from 'react';
import { Icon } from 'shared/elements/Icon';
import { Dialog } from 'shared/layers/Dialog';
import { Input } from 'shared/form/Input';
import { Block } from 'shared/layout/Block';
import { Button } from 'shared/elements/Button';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { useForm } from 'react-hook-form';
import * as Yup from 'yup';
import { yupResolver } from '@hookform/resolvers/yup';
import {
  createGroupMemberships,
  getAllUsers,
  updateGroup
} from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Group } from '../../../types';
import styles from './EditGroupsModal.module.css';
import { Search } from 'shared/form/Search';
import { Divider } from 'shared/elements/Divider';
import { Chip } from 'reablocks';
import { useMutation } from '@tanstack/react-query';

type EditGroupsModalProps = {
  canEdit: boolean;
  group: Group;
};

type UpdateGroupParams = {
  id: string;
  name: string;
  description: string;
};

type CreateGroupUserParams = {
  users: string[];
  groups: string[];
};

const updatingGroupSchema = Yup.object().shape({
  name: Yup.string().required('Required'),
  description: Yup.string().required('Required')
});

const EditGroupsModal: FC<EditGroupsModalProps> = ({ canEdit, group }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [groupUsers, setGroupUsers] = useState(group.users);
  const [isSearching, setIsSearching] = useState(false);
  const [isUpdatingGroups, setIsUpdatingGroups] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchValue, setSearchValue] = useState('');

  const updateGroupMutation = useMutation({
    mutationFn: (groupData: UpdateGroupParams) => updateGroup(groupData)
  });

  const createGroupUsersMutation = useMutation({
    mutationFn: (data: CreateGroupUserParams) => createGroupMemberships(data)
  });

  const searchMutation = useMutation({
    mutationFn: (search: string) => {
      const query = {
        filter: {
          pagination: { currentPageIndex: 1, pageSize: 10 },
          filtering: {
            tokens: [{ propertyKey: 'email', operator: ':', value: search }],
            operation: 'and'
          }
        }
      };
      return getAllUsers({ queryKey: ['groupUsers', query] });
    }
  });

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, isValid, errors, touchedFields }
  } = useForm({
    mode: 'onChange',
    reValidateMode: 'onChange',
    resolver: yupResolver(updatingGroupSchema),
    defaultValues: {
      description: group.description,
      name: group.name
    }
  });

  const resultRenderer = result => <p>{result.email}</p>;
  const onSelectResult = user => {
    setSearchValue(user.email);
    setGroupUsers(users => [...new Set([...users, user.email])]);
  };

  const reseActions = useCallback(() => {
    setErrorMessage(null);
    setSuccessMessage(null);
  }, []);

  const onSubmit = useCallback(
    async ({ name, description }) => {
      reseActions();
      try {
        await updateGroupMutation.mutateAsync({
          id: group.id,
          name,
          description
        });
        setSuccessMessage('Successfully updated group');
        // TODO refetch all groups
      } catch (error) {
        const err = error as AxiosError;
        const errorRes = err?.response;
        const errorMsg = extractErrorMessage(errorRes?.data);
        setErrorMessage(
          errorMsg || 'An error occurred while updating new group'
        );
      }
    },
    [group.id, reseActions, updateGroupMutation]
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
        const res = await searchMutation.mutateAsync(value);
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
      await createGroupUsersMutation.mutateAsync({
        users: groupUsers,
        groups: [group.name]
      });
      // TODO: update user groups
      setSuccessMessage('Successfully updated groups users');
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while updating group users'
      );
    }
    setIsUpdatingGroups(false);
  }, [group.name, groupUsers, reseActions, createGroupUsersMutation]);

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
        header="Edit Group Details"
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
          <br />
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block disableLabelPadding label="Name" required></Block>
            <Input
              fullWidth
              placeholder="name"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('name')}
            />
            {errors?.name && touchedFields.name && <p>{errors.name.message}</p>}
            <br />
            <Block disableLabelPadding label="Description" required></Block>
            <Input
              fullWidth
              placeholder="description"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('description')}
            />
            {errors?.description && touchedFields.description && (
              <p>{errors.description.message}</p>
            )}
            <br />
            <Button type="submit" disabled={isSubmitting || !isValid} fullWidth>
              {isSubmitting ? 'Updating Group...' : 'Update Group'}
            </Button>
          </form>

          <div className={styles.groupUsers}>
            <Block disableLabelPadding label="Add Users"></Block>
            <Search
              fullWidth
              resultRenderer={resultRenderer}
              results={searchResults}
              onChange={handleSearch}
              value={searchValue}
              isLoading={isSearching}
              onResultSelect={onSelectResult}
            />
            <div className={styles.users}>
              <h5>Group Users</h5>
              <Divider />
              {groupUsers.length ? (
                <div>
                  {groupUsers.map((user, index) => (
                    <Chip className={styles.user} key={index}>
                      {user}
                    </Chip>
                  ))}
                </div>
              ) : (
                <p>No Users Available in this Group</p>
              )}
            </div>
            <Button
              disabled={isUpdatingGroups}
              size="small"
              fullWidth
              onClick={updateGroupMemberships}
            >
              Update Group Memberships
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
};

export default EditGroupsModal;