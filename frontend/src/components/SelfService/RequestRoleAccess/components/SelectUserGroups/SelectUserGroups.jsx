import { useState } from 'react'
import debounce from 'lodash/debounce'
import {
  Button,
  Divider,
  Form,
  Grid,
  Header,
  Icon,
  Label,
  Search,
} from 'semantic-ui-react'
import { useAuth } from 'auth/AuthProviderDefault'
import { ACCESS_SCOPE, STEPS } from '../../constants'
import { formatSearchResults } from './utils'

const SelectUserGroups = ({
  setCurrentStep,
  userGroups,
  setUserGroups,
  accessScope,
  setAccessScope,
}) => {
  const { sendRequestCommon } = useAuth()

  const [results, setResults] = useState([])
  const [cachedResults, setCachedResults] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const [searchValue, setSearchValue] = useState('')

  const handleSearchChange = (_e, { value }) => {
    setSearchValue(value)
    setIsLoading(true)

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false)
        setResults([])
        setMessages([])
        setSearchValue('')
        return
      }

      const newValue = value.toLocaleLowerCase()

      if (cachedResults.length) {
        const reformattedResults = formatSearchResults(cachedResults, newValue)
        setIsLoading(false)
        setResults(reformattedResults)
        return
      }

      const TYPEAHEAD_API = `/api/v3/auth/cognito/groups`
      sendRequestCommon(null, TYPEAHEAD_API, 'get').then((res) => {
        const data = res?.count ? res.data : []

        setCachedResults(data)
        const reformattedResults = formatSearchResults(data, newValue)

        setIsLoading(false)
        setResults(reformattedResults)
      })
    }, 300)
  }

  const handleResultSelect = (_e, { result }) => {
    const savedGroups = userGroups.map((group) => group.name)
    if (!savedGroups.includes(result.name)) {
      setSearchValue('')
      setUserGroups([...userGroups, result])
    }
  }

  const resultRenderer = (result) => (
    <Grid>
      <Grid.Row verticalAlign='middle'>
        <Grid.Column width={10}>
          <div style={{ display: 'flex' }}>
            <Icon name='users' style={{ flexShrink: 0, width: '30px' }} />
            <strong
              style={{
                display: 'inline-block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {result.description ? (
                <span>{`${result.name} - ${result.description}`}</span>
              ) : (
                <span>{result.name}</span>
              )}
            </strong>
          </div>
        </Grid.Column>
        <Grid.Column width={6} textAlign='right'>
          {result.account ? result.account : null}
        </Grid.Column>
      </Grid.Row>
    </Grid>
  )

  return (
    <div>
      <Divider horizontal />
      <Header as='h3'>Choose user groups</Header>
      <Divider horizontal />

      <Form widths='equal'>
        <Header as='h5'>Request Access Scope</Header>

        <Form.Field>
          <Form.Radio
            label='For Myself'
            name='self'
            value={ACCESS_SCOPE.SELF}
            checked={accessScope === ACCESS_SCOPE.SELF}
            onChange={() => setAccessScope(ACCESS_SCOPE.SELF)}
          />
        </Form.Field>
        <Form.Field>
          <Form.Radio
            label='For specific groups'
            name='others'
            value={ACCESS_SCOPE.OTHERS}
            checked={accessScope === ACCESS_SCOPE.OTHERS}
            onChange={() => setAccessScope(ACCESS_SCOPE.OTHERS)}
          />
        </Form.Field>

        <Header as='h5'>Groups for Access</Header>

        <Form.Field required>
          <Search
            fluid
            loading={isLoading}
            onResultSelect={handleResultSelect}
            onSearchChange={debounce(handleSearchChange, 500, {
              leading: true,
            })}
            results={results}
            resultRenderer={resultRenderer}
            value={searchValue}
            placeholder='Enter role here'
          />
          <Divider />

          <Label.Group>
            {userGroups.map((group, index) => (
              <Label key={index}>{group.name}</Label>
            ))}
          </Label.Group>

          <Divider horizontal />
        </Form.Field>
      </Form>
      <Divider horizontal />
      <div className='step-actions'>
        <Button primary onClick={() => setCurrentStep(STEPS.STEP_ONE)}>
          Back
        </Button>
        <Button
          primary
          onClick={() => setCurrentStep(STEPS.STEP_THREE)}
          disabled={!userGroups.length}
        >
          Next
        </Button>
      </div>
    </div>
  )
}

export default SelectUserGroups
