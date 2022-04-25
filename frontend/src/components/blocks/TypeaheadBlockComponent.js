import _ from 'lodash'
import React, { Component } from 'react'
import { Form, Icon, Label, Search } from 'semantic-ui-react'

class TypeaheadBlockComponent extends Component {
  constructor(props) {
    super(props)
    this.state = {
      isLoading: false,
      results: [],
      selectedValues: [],
      value: '',
    }
  }

  _handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (!e.target.value) {
        return
      }
      let values = this.state.selectedValues
      values.push(e.target.value)
      this.setState(
        {
          selectedValues: values,
          value: '',
          results: [],
        },
        () => {
          this.props.handleInputUpdate(values)
        }
      )
    }
  }

  handleSelectedValueDelete(value) {
    const selectedValues = (
      this.state.defaultValues || this.state.selectedValues
    )?.filter((item) => item !== value)
    this.setState({
      selectedValues,
    })
    this.props.handleInputUpdate(selectedValues)
  }

  handleResultSelect(e, { result }) {
    let values = this.state.selectedValues
    values.push(result.title)
    this.setState(
      {
        value: '',
        selectedValues: values,
      },
      () => {
        this.props.handleInputUpdate(values)
      }
    )
  }

  handleSearchChange(e, { value }) {
    const { typeahead, noQuery, resultsFormatter, shouldTransformResults } =
      this.props
    this.setState(
      {
        isLoading: true,
        value,
      },
      () => {
        this.props.handleInputUpdate(this.state.selectedValues)
      }
    )

    setTimeout(() => {
      if (value.length < 1) {
        return this.setState(
          {
            isLoading: false,
            results: [],
            value: '',
          },
          () => {
            this.props.handleInputUpdate(this.state.selectedValues)
          }
        )
      }

      const re = new RegExp(_.escapeRegExp(value), 'i')
      const isMatch = (result) => re.test(result.title)

      const TYPEAHEAD_API = noQuery
        ? typeahead
        : typeahead.replace('{query}', value)

      this.props
        .sendRequestCommon(null, TYPEAHEAD_API, 'get')
        .then((response) => {
          const source = shouldTransformResults
            ? resultsFormatter(response)
            : response
          const results = _.filter(source, isMatch)
          this.setState({
            isLoading: false,
            results,
          })
        })
    }, 300)
  }

  componentDidMount() {
    this.setState({
      defaultValue: this.props.defaultValue,
      required: this.props.required,
      label: this.props.label,
      selectedValues: this.props.defaultValues,
    })
  }

  render() {
    const { isLoading, results, selectedValues, value } = this.state

    const selectedValueLabels = selectedValues.map((selectedValue, index) => {
      return (
        <Label basic color={'red'} key={index}>
          {selectedValue}
          <Icon
            name='delete'
            onClick={() => this.handleSelectedValueDelete(selectedValue)}
          />
        </Label>
      )
    })

    let formattedResults = results

    return (
      <Form.Field required={this.state.required || false}>
        <label>{this.state.label || 'Enter Value'}</label>
        <Search
          fluid
          multiple
          defaultValue={this.state.defaultValue || ''}
          loading={isLoading}
          onResultSelect={this.handleResultSelect.bind(this)}
          onSearchChange={_.debounce(this.handleSearchChange.bind(this), 500, {
            leading: true,
          })}
          onKeyDown={this._handleKeyDown}
          results={formattedResults}
          value={value}
          showNoResults={false}
        />
        <br />
        {selectedValueLabels}
      </Form.Field>
    )
  }
}

export default TypeaheadBlockComponent
