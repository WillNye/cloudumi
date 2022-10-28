import { useState, useCallback, useMemo } from 'react'
import escapeRegExp from 'lodash/escapeRegExp'
import debounce from 'lodash/debounce'
import {
  Button,
  Divider,
  Form,
  Header,
  Search,
  Segment,
} from 'semantic-ui-react'
import { useAuth } from 'auth/AuthProviderDefault'
import { ROLE_CREATION_STEPS } from '../../constants'

const RequestForm = ({ formData, setCurrentStep, setFormData }) => {
  const [isLoadingAccount, setIsLoadingAccount] = useState(false)
  const [searchValue, setSearchValue] = useState(formData?.account?.title || '')
  const [selectedAccount, setSelectedAccount] = useState(
    formData?.account || null
  )
  const [accountResults, setAccountResults] = useState([])
  const [roleName, setRoleName] = useState(formData?.roleName || '')
  const [description, setDescription] = useState(formData?.description || '')
  const [roleNameError, setRoleNameError] = useState(null)

  const { sendRequestCommon } = useAuth()

  const debouncedSearchFilter = useMemo(
    () =>
      debounce((value) => {
        setIsLoadingAccount(true)
        setAccountResults([])

        if (value.length < 1) {
          setIsLoadingAccount(false)
          setSelectedAccount(null)
          return
        }

        const re = new RegExp(escapeRegExp(value), 'i')
        const TYPEAHEAD_API = `/api/v2/policies/typeahead?resource=account&search=${value}`
        sendRequestCommon(null, TYPEAHEAD_API, 'get')
          .then((source) => {
            if (!source) {
              return
            }
            const resultsAccount = source.filter((result) =>
              re.test(result.title)
            )
            setAccountResults(resultsAccount)
          })
          .finally(() => {
            setIsLoadingAccount(false)
          })
      }, 300),
    [] // eslint-disable-line react-hooks/exhaustive-deps
  )

  const handleSearchChange = (_e, { value }) => {
    setSearchValue(value)
    debouncedSearchFilter(value)
  }

  const handleResultSelect = (_e, { result }) => {
    setSelectedAccount(result)
    setSearchValue(result.title)
  }

  const handleSubmit = useCallback(() => {
    setFormData({
      roleName,
      account: selectedAccount,
      description,
    })
    setCurrentStep(ROLE_CREATION_STEPS.STEP_TWO)
  }, [roleName, description, selectedAccount]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Segment basic>
      <Header size='medium'>Enter Role Details</Header>
      <Divider horizontal />

      <Form>
        <Form.Input
          required
          fluid
          error={roleNameError}
          label='Role Name'
          name='role_name'
          value={roleName}
          maxLength={64}
          placeholder='Role name'
          onChange={(_e, { value }) => {
            setRoleNameError(null)
            setRoleName(value)
            if (!/^[a-zA-Z_0-9+=,.@-_]+$/.test(value)) {
              setRoleNameError(
                'Role name should only contain alphanumeric characters and +=,.@_-'
              )
            }
          }}
        />
        <Form.Field required>
          <label>Account ID</label>
          <Search
            loading={isLoadingAccount}
            name='account_id'
            placeholder='Search for account by ID'
            onResultSelect={handleResultSelect}
            onSearchChange={handleSearchChange}
            results={accountResults}
            value={searchValue}
            fluid
          />
        </Form.Field>
        <Form.Input
          fluid
          label='Description'
          name='description'
          value={description}
          placeholder='Optional description'
          onChange={(_e, { value }) => setDescription(value)}
        />

        <Divider horizontal />

        <div className='role-creation__step-actions'>
          <Button
            primary
            onClick={handleSubmit}
            disabled={
              !selectedAccount || !(roleName || '').trim() || roleNameError
            }
          >
            Next
          </Button>
        </div>
      </Form>
    </Segment>
  )
}

export default RequestForm
