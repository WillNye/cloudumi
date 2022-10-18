import _, { debounce } from 'lodash'
import { useCallback, useState, useMemo } from 'react'
import { Form, Header, Icon, Label, Search } from 'semantic-ui-react'

export const TypeaheadBlockComponent = (props) => {
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState([])
  const [selectedValues, setSelectedValues] = useState(
    props.defaultValues ?? []
  )
  const [value, setValue] = useState(props.defaultValue ?? '')

  const { typeahead, noQuery, resultsFormatter, shouldTransformResults } = props

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (!e.target.value) {
        return
      }
      const values = [...selectedValues]
      values.push(e.target.value)
      setSelectedValues(values)
      setResults([])
      setValue('')
      props.handleInputUpdate(values)
    }
  }

  const handleSelectedValueDelete = useCallback(
    (value) => {
      const values = selectedValues?.filter((item) => item !== value)
      setSelectedValues(values)
      props.handleInputUpdate(values)
    },
    [selectedValues] // eslint-disable-line
  )

  const handleResultSelect = useCallback(
    (e, { result }) => {
      let values = [...selectedValues]
      values.push(result.title)

      setSelectedValues(values)

      props.handleInputUpdate(values)
    },
    [selectedValues] // eslint-disable-line
  )

  const debouncedSearchFilter = useMemo(
    () =>
      debounce((value) => {
        setIsLoading(true)

        if (value.length < 1) {
          setIsLoading(false)
          setResults([])
          setValue('')
          props.handleInputUpdate(selectedValues)
          return
        }

        const re = new RegExp(_.escapeRegExp(value), 'i')
        const isMatch = (result) => re.test(result.title)

        const TYPEAHEAD_API = noQuery
          ? typeahead
          : typeahead.replace('{query}', value)

        props.sendRequestCommon(null, TYPEAHEAD_API, 'get').then((response) => {
          const source = shouldTransformResults
            ? resultsFormatter(response)
            : response
          const results = _.filter(source, isMatch)

          setIsLoading(false)
          setResults(results)
        })
      }, 300),
    [noQuery, shouldTransformResults, selectedValues] // eslint-disable-line
  )

  const handleSearchChange = useCallback(
    (e, { value }) => {
      setValue(value)

      props.handleInputUpdate(selectedValues)
      debouncedSearchFilter(value)
    },
    [selectedValues, debouncedSearchFilter] // eslint-disable-line
  )

  const selectedValueLabels = selectedValues.map((selectedValue, index) => (
    <Label basic color='blue' key={index}>
      {selectedValue}
      <Icon
        name='delete'
        onClick={() => handleSelectedValueDelete(selectedValue)}
      />
    </Label>
  ))

  return (
    <Form.Field required={props.required || false}>
      <label>{props.label || 'Enter Value'}</label>
      <Search
        fluid
        multiple
        loading={isLoading}
        onResultSelect={handleResultSelect}
        onSearchChange={_.debounce(handleSearchChange, 500, {
          leading: true,
        })}
        onKeyDown={handleKeyDown}
        results={results}
        value={value}
        showNoResults={false}
      />
      <br />
      {selectedValues.length ? (
        <div>
          {props.defaultTitle && <Header as='h6'>{props.defaultTitle}</Header>}
          <Label.Group size='tiny'>{selectedValueLabels}</Label.Group>
        </div>
      ) : (
        <></>
      )}
    </Form.Field>
  )
}

export default TypeaheadBlockComponent
