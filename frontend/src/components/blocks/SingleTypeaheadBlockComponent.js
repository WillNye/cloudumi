import _ from 'lodash'
import React, { useCallback, useState } from 'react'
import { Form, Search } from 'semantic-ui-react'

const SingleTypeaheadBlockComponent = (props) => {
  const { defaultValue, required, label, typeahead } = props

  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState([])
  const [value, setValue] = useState(defaultValue ?? '')

  const handleResultSelect = (e, { result }) => {
    setValue(result.title)
    props.handleInputUpdate(result.title)
  }

  const handleSearchChange = useCallback(
    (_e, { value }) => {
      setIsLoading(true)
      setValue(value)
      props.handleInputUpdate(value)

      setTimeout(() => {
        if (value.length < 1) {
          setIsLoading(false)
          setResults([])
          setValue('')
          props.handleInputUpdate('')
        }

        const re = new RegExp(_.escapeRegExp(value), 'i')
        const isMatch = (result) => re.test(result.title)

        const TYPEAHEAD_API = typeahead.replace('{query}', value)
        props.sendRequestCommon(null, TYPEAHEAD_API, 'get').then((source) => {
          const results = _.filter(source, isMatch)

          setIsLoading(false)
          setResults(results)
        })
      }, 300)
    },
    [typeahead] // eslint-disable-line
  )

  return (
    <Form.Field required={required || false}>
      <label>{label || 'Enter Value'}</label>
      <Search
        fluid
        defaultValue={defaultValue || ''}
        loading={isLoading}
        onResultSelect={handleResultSelect}
        onSearchChange={_.debounce(handleSearchChange, 500, {
          leading: true,
        })}
        results={results}
        value={value}
      />
    </Form.Field>
  )
}

export default SingleTypeaheadBlockComponent
