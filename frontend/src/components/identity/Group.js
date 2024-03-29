import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  Button,
  Header,
  Popup,
  Table,
  Icon,
  Form,
  TextArea,
} from 'semantic-ui-react'
import { useAuth } from '../../auth/AuthProviderDefault'
import { useForm } from 'react-hook-form'
import SemanticDatepicker from 'react-semantic-ui-datepickers'
import { DateTime } from 'luxon'

const IdentityGroupEdit = () => {
  const auth = useAuth()
  const { sendRequestCommon } = auth
  const { idpName, groupName } = useParams()

  const [header, setHeader] = useState(null)
  const [attributes, setAttributes] = useState(null)
  const [groupDetails, setGroupDetails] = useState(null)
  const [groupExpiration, setGroupExpiration] = useState(null)
  const [justification, setJustification] = useState(null)
  const {
    register,
    handleSubmit,
    // formState: { errors },
  } = useForm()
  const onSubmit = async (data) => {
    const resJson = await sendRequestCommon(
      data,
      '/api/v3/identities/group/' + idpName + '/' + groupName
    )
    // TODO: Post data and render response message/error in a generic way
    console.log(data)
    console.log(resJson)
  }

  useEffect(() => {
    async function fetchDetails() {
      const resJson = await sendRequestCommon(
        null,
        '/api/v3/identities/group/' + idpName + '/' + groupName,
        'get'
      )
      if (!resJson) {
        return
      }
      setGroupDetails(resJson)

      // Set headers
      if (resJson?.headers) {
        setHeader(
          resJson.headers.map(function (header) {
            return (
              <Table.Row>
                <Table.Cell width={4}>{header.key}</Table.Cell>
                <Table.Cell>{header.value}</Table.Cell>
              </Table.Row>
            )
          })
        )
      }

      // Show attributes
      // TODO: How do we use a custom Semantic UI Toggle checkbox? Can't figure it out with react-hook-form
      if (resJson?.attributes) {
        setAttributes(
          resJson.attributes.map(function (attribute) {
            if (attribute.type === 'bool') {
              return (
                <Form.Field>
                  <div style={{ display: 'block', width: '50px;' }}>
                    <input
                      type='checkbox'
                      style={{ display: 'inline' }}
                      defaultChecked={attribute.value}
                      {...register(attribute.name)}
                    />
                    {'    '}
                    <Popup
                      trigger={
                        <label style={{ display: 'inline' }}>
                          {attribute.friendly_name}
                        </label>
                      }
                      content={attribute.description}
                      position='right center'
                      size='mini'
                    />
                    {/* <div className={"ui fitted toggle checkbox"}> */}
                    {/* <Input toggle type="checkbox" {...register(attribute.name)} /> */}
                    {/* <Controller
                name={attribute.name}
                control={control}
                render={({ field }) => <Checkbox toggle {...field} />}
              /> */}

                    {/* <Checkbox toggle {...register(attribute.name)} /> */}
                    {/* <Controller
                name={attribute.name}
                control={control}
                error={!!errors.checkBox}
                defaultValue={false}
                as={Form.Checkbox}
                valueName="checked"
                onChangeName="onPress"
                onChange={(e) => {
                  console.log(e)
                  // data.checked
                }

                }
                render={({
                  field: { onChange, onBlur, value, name, ref },
                  fieldState: { invalid, isTouched, isDirty, error },
                  formState,
                }) => (
                  <Ref innerRef={ref}>
                  <Form.Checkbox
                    toggle
                    onChange={onChange}
                    checked={value}
                  />
                  </Ref>
                )} */}
                    {/* render={({ field }) => <Form.Checkbox toggle {...field} />} */}
                    {/* /> */}
                    {/* Get them to the point where they can play around. Keep Step 3 manual. It will be*/}
                    {/* Automated in the future but just not now */}
                    {/* Experience to devs is the most important */}
                  </div>
                </Form.Field>
              )
            } else if (attribute.type === 'array') {
              return (
                <p>
                  <Popup
                    trigger={<label>{attribute.friendly_name}</label>}
                    content={attribute.description}
                    position='top center'
                    size='mini'
                  />

                  <input
                    defaultValue={attribute.value}
                    {...register(attribute.name)}
                  />
                </p>
              )
            } else {
              return null
            }
          })
        )
      }
    }
    fetchDetails()
  }, [sendRequestCommon]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    console.log(groupDetails)
  }, [groupDetails])

  return (
    <>
      <Header as='h3'>Group Details</Header>
      <Table celled striped definition>
        {header}
      </Table>
      <Header as='h3'>Group Attributes</Header>

      <Form onSubmit={handleSubmit(onSubmit)}>
        {attributes}
        <Button primary ype='submit'>
          Save
        </Button>
      </Form>
      <br />
      <Header as='h3'>Add Users to Group</Header>
      {/* Bulk Add / Bulk Remove groups */}
      {/* TODO: Implement multi-select table  to allow deleting multiple groups at once */}
      <Form>
        <TextArea placeholder='Comma or Newline-Separated List of Users' />
        <br />
        <br />
        <Form.Field>
          <Header as='h1'>
            <Header.Subheader>Justification</Header.Subheader>
          </Header>
          <TextArea
            placeholder='Reason for requesting access'
            onChange={(e) => {
              setJustification(e.target.value)
              console.log(justification)
            }}
          />
        </Form.Field>
        <Form.Field>
          <Header as='h1'>
            <Header.Subheader>(Optional) Expiration</Header.Subheader>
          </Header>
          <SemanticDatepicker
            filterDate={(date) => {
              const now = new Date()
              return date >= now
            }}
            onChange={(e, data) => {
              if (!data?.value) {
                setGroupExpiration(null)
                return
              }
              const dateObj = DateTime.fromJSDate(data.value)
              const dateString = dateObj.toFormat('yyyyMMdd')
              setGroupExpiration(parseInt(dateString))
              console.log(groupExpiration)
            }}
            type='basic'
            compact
          />
        </Form.Field>
        {/* TODO: Does bulk request need to be a feature? <Button
          content={"Submit for Review"}
          // onClick={handleRequestGroups}
          // style={{
          //   width: "50%",
          //   display: "inline-block",
          //   textAlign: "center",
          // }}
          positive
        // attached="right"
        /> */}
        <Button
          content={'Add Users'}
          // onClick={handleAdminAddGroups}
          // style={{
          //   width: "50%",
          //   display: "inline-block",
          //   textAlign: "center",
          //   maxWidth: "20em",
          // }}
          // floated={"right"}
          color={'green'}
        />
        <br />
        <Header as='h3'>Members</Header>
      </Form>
      <Table celled striped>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>Username</Table.HeaderCell>
            <Table.HeaderCell>Remove</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {groupDetails?.group?.members?.map((member) => (
            <Table.Row>
              <Table.Cell>{member.username}</Table.Cell>
              <Table.Cell>
                <Button negative icon labelPosition='right'>
                  Request Removal
                  <Icon name='delete' />
                </Button>
                <Button color={'orange'} icon labelPosition='right'>
                  Remove
                  <Icon name='delete' />
                </Button>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
      <Header as='h3'>Requests</Header>
    </>
  )
}

export default IdentityGroupEdit
