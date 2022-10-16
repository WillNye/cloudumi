import { useState } from 'react'
import {
  Button,
  Divider,
  Form,
  Grid,
  Header,
  Icon,
  Message,
  Search,
  Segment,
} from 'semantic-ui-react'
import isString from 'lodash/isString'
import debounce from 'lodash/debounce'
import { useAuth } from 'auth/AuthProviderDefault'
import DateTimePicker from 'components/blocks/DateTimePicker'
import { STEPS } from '../../constants'

const SelectIdentity = ({
  setRole,
  setCurrentStep,
  role,
  expirationDate,
  setExpirationDate,
}) => {
  const { sendRequestCommon } = useAuth()

  const [results, setResults] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isRoleLoading, setIsRoleLoading] = useState(false)
  const [messages, setMessages] = useState([])
  const [searchValue, setSearchValue] = useState(role?.name || '')

  const getRoleDetail = (endpoint, principal) => {
    sendRequestCommon(null, endpoint, 'get').then((response) => {
      if (!response) {
        return
      }
      // if the given role doesn't exist.
      if (response.status === 404) {
        setRole(null)
        setIsLoading(false)
        setIsRoleLoading(false)
        setMessages([response.message])
      } else {
        response.principal = principal
        setRole(response)
        setIsLoading(false)
        setIsRoleLoading(false)
        setMessages([])
      }
    })
  }

  const handleSearchChange = (_e, { value }) => {
    setSearchValue(value)
    setIsLoading(true)
    setRole(null)

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false)
        setResults([])
        setMessages([])
        setSearchValue('')
        return
      }

      const TYPEAHEAD_API = `/api/v2/typeahead/self_service_resources?typeahead=${value}`
      sendRequestCommon(null, TYPEAHEAD_API, 'get').then((results) => {
        const reformattedResults = results.map((res, idx) => {
          return {
            id: idx,
            title: res.display_text,
            ...res,
          }
        })

        setIsLoading(false)
        setResults(reformattedResults)
      })
    }, 300)
  }

  const handleResultSelect = (e, { result }) => {
    const value = isString(result.title) ? result.title.trim() : result.title

    setIsRoleLoading(true)
    setSearchValue(value)

    getRoleDetail(result.details_endpoint, result.principal)
  }

  const resultRenderer = (result) => (
    <Grid>
      <Grid.Row verticalAlign='middle'>
        <Grid.Column width={10}>
          <div style={{ display: 'flex' }}>
            <Icon name={result.icon} style={{ flexShrink: 0, width: '30px' }} />
            <strong
              style={{
                display: 'inline-block',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {result.icon === 'users' ? (
                <span style={{ color: '#286f85' }}>{result.display_text}</span>
              ) : (
                <span>{result.display_text}</span>
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
    <Segment basic loading={isRoleLoading}>
      <Header as='h3'>Choose an identity</Header>
      <Divider horizontal />
      <p>
        Search and select the AWS IAM Role you would like to request access to.
      </p>

      <Divider horizontal />

      {messages.length > 0 ? (
        <Message negative>
          <Message.Header>
            We found some problems for this request.
          </Message.Header>
          <Message.List>
            {messages.map((message, index) => (
              <Message.Item key={index}>{message}</Message.Item>
            ))}
          </Message.List>
        </Message>
      ) : (
        <></>
      )}

      <Header as='h5'>Role</Header>

      <Form widths='equal'>
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
        </Form.Field>
      </Form>
      <Divider horizontal />
      <Header as='h5'>Access Expiration</Header>

      <DateTimePicker
        defaultDate={expirationDate}
        onDateSelectorChange={(value) => setExpirationDate(value)}
      />

      <Divider horizontal />

      <div className='step-actions'>
        <Button
          primary
          onClick={() => setCurrentStep(STEPS.STEP_TWO)}
          disabled={!Boolean(role)}
        >
          Next
        </Button>
      </div>
    </Segment>
  )
}

export default SelectIdentity
