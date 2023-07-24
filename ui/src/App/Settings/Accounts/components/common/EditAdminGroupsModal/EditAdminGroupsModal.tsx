import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import {
  PartialWebResponse,
  addAdminGroups,
  deleteAdminGroups,
  getAdminGroups,
  getAllGroups
} from 'core/API/settings';
import { extractErrorMessage } from 'core/API/utils';
import { FC, Fragment, useCallback, useEffect, useRef, useState } from 'react';
import { Button } from 'shared/elements/Button';
import { Chip } from 'shared/elements/Chip';
import { Divider } from 'shared/elements/Divider';
import { Icon } from 'shared/elements/Icon';
import { LineBreak } from 'shared/elements/LineBreak';
import { Notification, NotificationType } from 'shared/elements/Notification';
import { Search } from 'shared/form/Search';
import { Dialog } from 'shared/layers/Dialog';
import { Block } from 'shared/layout/Block';
import styles from './EditAdminGroupsModal.module.css';
import { toast } from 'react-toastify';

type GroupsParams = {
  groups: string[];
};

const EditAdminGroupsModal: FC<{
  canEdit?: boolean;
}> = ({ canEdit }) => {
  const [showDialog, setShowDialog] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [adminGroups, setAdminGroups] = useState<string[]>([]);
  const [groupEdition, setGroupEdition] = useState({
    add: [],
    remove: []
  });
  const [isSearching, setIsSearching] = useState(false);
  const [isUpdatingGroups, setIsUpdatingGroups] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchValue, setSearchValue] = useState('');

  const queryClient = useQueryClient();

  const { data: currentAdminGroups } = useQuery({
    queryKey: ['adminGroups'],
    queryFn: async () => getAdminGroups(),
    select: data => {
      return data?.data ?? [];
    }
  });

  useEffect(() => {
    setAdminGroups(currentAdminGroups ?? []);
  }, [currentAdminGroups]);

  const { mutateAsync: addGroupsMutation } = useMutation({
    mutationFn: async (data: GroupsParams) => addAdminGroups({ ...data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`adminGroups`] });
    }
  });

  const { mutateAsync: deleteGroupsMutation } = useMutation({
    mutationFn: (data: GroupsParams) => deleteAdminGroups({ ...data })
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

  const resultRenderer = result => <p>{result.name}</p>;
  const onSelectResult = group => {
    setSearchValue(group.name);
    setAdminGroups([...new Set([...adminGroups, group.name])]);

    if (groupEdition.remove.includes(group.name)) {
      setGroupEdition({
        ...groupEdition,
        remove: groupEdition.remove.filter(u => u != group.name)
      });
    } else {
      setGroupEdition({
        ...groupEdition,
        add: [...new Set([...groupEdition.add, group.name])]
      });
    }
  };

  const handleDeleteChip = (group, index) => {
    if (adminGroups.length == 1) {
      toast.error(`Cannot remove last group from admin groups`);
      return;
    }

    setAdminGroups([
      ...new Set([...adminGroups.filter((ug, i) => i != index)])
    ]);

    if (groupEdition.add.includes(group)) {
      setGroupEdition({
        ...groupEdition,
        add: groupEdition.add.filter(u => u != group)
      });
    } else {
      setGroupEdition({
        ...groupEdition,
        remove: [...new Set([...groupEdition.remove, group])]
      });
    }
  };

  const resetActions = useCallback(() => {
    setErrorMessage(null);
    setSuccessMessage(null);
  }, []);

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
    if (groupEdition.add.length == 0 && groupEdition.remove.length == 0) {
      toast.info('Nothing to update');
    }

    resetActions();
    setIsUpdatingGroups(true);
    try {
      const responses: PartialWebResponse[] = [];

      if (groupEdition.add.length) {
        responses.push(
          (
            await addGroupsMutation({
              groups: groupEdition.add
            })
          ).data
        );
      }

      if (groupEdition.remove.length) {
        responses.push(
          (
            await deleteGroupsMutation({
              groups: groupEdition.remove
            })
          ).data
        );
      }

      const errorMessages = [];

      for (const res of responses) {
        if (!res) {
          continue;
        }

        if (res.status == 'error') {
          errorMessages.push(res.data?.message as string);
        }
      }

      if (errorMessages.length > 0) {
        setErrorMessage(errorMessages.join('\n'));
      } else {
        setGroupEdition({ add: [], remove: [] });
        setSuccessMessage('Successfully updated admin groups');
      }
    } catch (error) {
      const err = error as AxiosError;
      const errorRes = err?.response;
      const errorMsg = extractErrorMessage(errorRes?.data);
      setErrorMessage(
        errorMsg || 'An error occurred while updating user groups'
      );
    }
    setIsUpdatingGroups(false);
  }, [
    resetActions,
    groupEdition.add,
    groupEdition.remove,
    addGroupsMutation,
    deleteGroupsMutation
  ]);

  if (!(canEdit ?? true)) {
    return <Fragment />;
  }

  return (
    <div className={styles.container}>
      <Button onClick={() => setShowDialog(true)}>Edit Admin Groups</Button>

      <Dialog
        showDialog={showDialog}
        setShowDialog={setShowDialog}
        disablePadding
        header="Edit Admin Groups"
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
          <div className={styles.userGroups}>
            {
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
            }
            <div className={styles.groups}>
              <h5>User Groups</h5>
              <Divider />
              {adminGroups.length ? (
                <div>
                  {adminGroups.map((group, index) => (
                    <Chip className={styles.group} key={index}>
                      {group}
                      {
                        <>
                          {' '}
                          <Icon
                            name="close"
                            size="small"
                            onClick={() => handleDeleteChip(group, index)}
                          />
                        </>
                      }
                    </Chip>
                  ))}
                </div>
              ) : (
                <p>No Groups Availables for this User</p>
              )}
            </div>
            <Button
              disabled={isUpdatingGroups}
              size="small"
              fullWidth
              onClick={updateGroupMemberships}
            >
              Update Admin Groups
            </Button>
          </div>
          <LineBreak />
        </div>
      </Dialog>
    </div>
  );
};

export default EditAdminGroupsModal;
