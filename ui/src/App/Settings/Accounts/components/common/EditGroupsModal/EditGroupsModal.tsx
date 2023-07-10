import { FC, Fragment, useCallback, useMemo, useRef, useState } from 'react';
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
  deleteGroupMemberships,
  getAllUsers,
  updateGroup
} from 'core/API/settings';
import { AxiosError } from 'axios';
import { extractErrorMessage } from 'core/API/utils';
import { Group } from '../../../types';
import styles from './EditGroupsModal.module.css';
import { Search } from 'shared/form/Search';
import { Divider } from 'shared/elements/Divider';
import { useMutation } from '@tanstack/react-query';
import { LineBreak } from 'shared/elements/LineBreak';
import { Chip } from 'shared/elements/Chip';

type EditGroupsModalProps = {
  canEdit?: boolean;
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
  check_deleted?: boolean;
};

const updatingGroupSchema = Yup.object().shape({
  name: Yup.string().required('Required'),
  description: Yup.string().required('Required')
});

// eslint-disable-next-line complexity
const EditGroupsModal: FC<EditGroupsModalProps> = ({ canEdit, group }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [groupUsers, setGroupUsers] = useState(group.users);
  const [groupEdition, setGroupEdition] = useState({
    add: [],
    remove: []
  });
  const [isSearching, setIsSearching] = useState(false);
  const [isUpdatingGroups, setIsUpdatingGroups] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchValue, setSearchValue] = useState('');

  const { mutateAsync: updateGroupMutation } = useMutation({
    mutationFn: (groupData: UpdateGroupParams) => updateGroup(groupData)
  });

  const { mutateAsync: createGroupUsersMutation } = useMutation({
    mutationFn: (data: CreateGroupUserParams) =>
      createGroupMemberships({ ...data })
  });

  const { mutateAsync: deleteGroupUsersMutation } = useMutation({
    mutationFn: (data: CreateGroupUserParams) =>
      deleteGroupMemberships({ ...data })
  });

  const { mutateAsync: searchMutation } = useMutation({
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
    setGroupUsers([...new Set([...groupUsers, user.email])]);

    if (groupEdition.remove.includes(user.email)) {
      setGroupEdition({
        ...groupEdition,
        remove: groupEdition.remove.filter(u => u != user.email)
      });
    } else {
      setGroupEdition({
        ...groupEdition,
        add: [...new Set([...groupEdition.add, user.email])]
      });
    }
  };

  const handleDeleteChip = (user, index) => {
    setGroupUsers([...new Set([...groupUsers.filter((ug, i) => i != index)])]);

    if (groupEdition.add.includes(user)) {
      setGroupEdition({
        ...groupEdition,
        add: groupEdition.add.filter(u => u == user)
      });
    } else {
      setGroupEdition({
        ...groupEdition,
        remove: [...new Set([...groupEdition.remove, user])]
      });
    }
  };

  const resetActions = useCallback(() => {
    setErrorMessage(null);
    setSuccessMessage(null);
  }, []);

  const onSubmit = useCallback(
    async ({ name, description }) => {
      resetActions();
      try {
        await updateGroupMutation({
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
    [group.id, resetActions, updateGroupMutation]
  );

  let reqDelay = useRef<any>();

  const handleSearch = useCallback(
    async e => {
      const value = e.target.value;
      setSearchValue(value);
      if (!value) {
        setSearchResults([]);
        return;
      }

      clearTimeout(reqDelay.current);
      reqDelay.current = setTimeout(async () => {
        setIsSearching(true);
        try {
          const res = await searchMutation(value);
          setSearchResults(res.data.data);
        } catch (error) {
          // TODO: Properly handle error
          console.error(error);
        }
        setIsSearching(false);
      }, 500);
    },
    [searchMutation]
  );

  const updateGroupMemberships = useCallback(async () => {
    resetActions();
    setIsUpdatingGroups(true);
    try {
      const responses = await Promise.all([
        groupEdition.add.length
          ? createGroupUsersMutation({
              users: groupEdition.add, //groupEdition.add,
              groups: [group.name]
            })
          : null,
        groupEdition.remove.length
          ? deleteGroupUsersMutation({
              users: groupEdition.remove,
              groups: [group.name]
            })
          : null
      ]);

      // Process the messages received in the response
      const successMessages = [];
      const errorMessages = [];
      for (const res of responses) {
        if (!res) {
          continue;
        }

        res.data.data.message.forEach(message => {
          if (message.type === 'success') {
            successMessages.push(message.message);
          } else if (message.type === 'error') {
            errorMessages.push(message.message);
          }
        });
      }

      // Set the success and error messages
      if (successMessages.length > 0) {
        setSuccessMessage(successMessages.join(' '));
      }
      if (errorMessages.length > 0) {
        setErrorMessage(errorMessages.join(' '));
      } else {
        // Reset the group edition
        setGroupEdition({ add: [], remove: [] });
      }
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while updating group users'
      );
    }
    setIsUpdatingGroups(false);
  }, [
    resetActions,
    createGroupUsersMutation,
    groupEdition.add,
    groupEdition.remove,
    group.name,
    deleteGroupUsersMutation
  ]);

  const isDisabled = useMemo(
    () => group.managed_by != 'MANUAL',
    [group.managed_by]
  );

  if (!(canEdit ?? true)) {
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
          <LineBreak />
          <form onSubmit={handleSubmit(onSubmit)}>
            <Block disableLabelPadding label="Name" required></Block>
            <Input
              fullWidth
              placeholder="name"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('name', { disabled: isDisabled })}
            />
            {errors?.name && touchedFields.name && <p>{errors.name.message}</p>}
            <LineBreak />
            <Block disableLabelPadding label="Description" required></Block>
            <Input
              fullWidth
              placeholder="description"
              autoCapitalize="none"
              autoCorrect="off"
              {...register('description', {
                disabled: isDisabled
              })}
            />
            {errors?.description && touchedFields.description && (
              <p>{errors.description.message}</p>
            )}
            <LineBreak />
            <Button
              type="submit"
              disabled={isSubmitting || !isValid || isDisabled}
              fullWidth
            >
              {isSubmitting ? 'Updating Group...' : 'Update Group'}
            </Button>
          </form>

          <div className={styles.groupUsers}>
            {!isDisabled && (
              <>
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
              </>
            )}
            <div className={styles.users}>
              <h5>Group Users</h5>
              <Divider />
              {groupUsers.length ? (
                <div>
                  {groupUsers.map((user, index) => (
                    <Chip className={styles.user} key={index}>
                      {user}
                      {!isDisabled && (
                        <>
                          {' '}
                          <Icon
                            name="close"
                            size="small"
                            onClick={() => handleDeleteChip(user, index)}
                          />
                        </>
                      )}
                    </Chip>
                  ))}
                </div>
              ) : (
                <p>No Users Available in this Group</p>
              )}
            </div>
            <Button
              disabled={isUpdatingGroups || isDisabled}
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
