import _ from 'lodash'
import React, { useCallback, useEffect, useState } from 'react'
import { Form, Icon, Label, Search } from 'semantic-ui-react'

const TypeaheadBlockComponent = (props) => {
  const [isLoading, setIsLoading] = useState(false)
  const [results, setResults] = useState([])
  const [selectedValues, setSelectedValues] = useState(
    props.defaultValues ?? []
  )
  const [value, setValue] = useState(props.defaultValue ?? '')

  useEffect(function onMount() {}, [])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (!e.target.value) {
        return
      }
      let values = this.state.selectedValues
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

  const handleSearchChange = (e, { value }) => {
    const { typeahead, noQuery, resultsFormatter, shouldTransformResults } =
      props

    setIsLoading(true)
    setValue(value)

    props.handleInputUpdate(this.state.selectedValues)

    setTimeout(() => {
      if (value.length < 1) {
        setIsLoading(false)
        setResults([])
        setValue('')
        props.handleInputUpdate(this.state.selectedValues)

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
    }, 300)
  }

  const selectedValueLabels = selectedValues.map((selectedValue, index) => {
    return (
      <Label basic color={'red'} key={index}>
        {selectedValue}
        <Icon
          name='delete'
          onClick={() => handleSelectedValueDelete(selectedValue)}
        />
      </Label>
    )
  })

  let formattedResults = results

  return (
    <Form.Field required={props.required || false}>
      <label>{props.label || 'Enter Value'}</label>
      <Search
        fluid
        multiple
        loading={isLoading}
        onResultSelect={handleResultSelect}
        onSearchChange={(e, data) =>
          _.debounce(() => handleSearchChange(e, data), 500, {
            leading: true,
          })
        }
        onKeyDown={handleKeyDown}
        results={formattedResults}
        value={value}
        showNoResults={false}
      />
      <br />
      {selectedValueLabels}
    </Form.Field>
  )
}

export default TypeaheadBlockComponent
