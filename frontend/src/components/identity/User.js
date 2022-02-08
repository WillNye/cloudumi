/* eslint-disable react-hooks/exhaustive-deps */
import { DateTime } from "luxon";
import React, { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import ReactMarkdown from "react-markdown";
import { useParams } from "react-router-dom";
import SemanticDatepicker from "react-semantic-ui-datepickers";
import {
  Button,
  Form,
  Header,
  Icon,
  Message,
  Popup,
  Table,
  TextArea,
} from "semantic-ui-react";
import { useAuth } from "../../auth/AuthProviderDefault";

const IdentityUserEdit = () => {
  const auth = useAuth();
  const { sendRequestCommon } = auth;
  const { idpName, userName } = useParams();

  const [header, setHeader] = useState(null);
  const [attributes, setAttributes] = useState(null);
  const [userDetails, setuserDetails] = useState(null);
  const [groupExpiration, setGroupExpiration] = useState(null);
  const [justification, setJustification] = useState(null);
  const [bulkGroupEditField, setBulkGroupEditField] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [statusMessage, setStatusMessage] = useState(null);

  const {
    // control,
    register,
    // handleSubmit,
    // formState: { errors },
  } = useForm();
  // const onSubmit = async (data) => {
  //   const resJson = await sendRequestCommon(
  //     data,
  //     "/api/v3/identities/user/" + idpName + "/" + userName
  //   );
  //   // TODO: Post data and render response message/error in a generic way
  //   console.log(data);
  //   //console.log(resJson)
  // };

  const handleAddGroups = useCallback(
    async (evt, action) => {
      const data = {
        user: userName,
        justification: justification,
        groupExpiration: groupExpiration,
        bulkGroupEditField: bulkGroupEditField,
        idpName: idpName,
      };

      const resJson = await sendRequestCommon(
        data,
        "/api/v3/identities/requests/groups"
      );
      console.log(resJson);
      if (resJson.status !== "success") {
        setErrorMessage(JSON.stringify(resJson));
      } else {
        setStatusMessage(
          <ReactMarkdown linkTarget="_blank" children={resJson.message} />
        );
      }
    },
    [
      justification,
      groupExpiration,
      bulkGroupEditField,
      idpName,
      sendRequestCommon,
    ]
  );

  useEffect(() => {
    async function fetchDetails() {
      const resJson = await sendRequestCommon(
        null,
        "/api/v3/identities/user/" + idpName + "/" + userName,
        "get"
      );
      if (!resJson) {
        return;
      }
      setuserDetails(resJson);

      // Set headers
      if (resJson?.headers) {
        setHeader(
          resJson.headers.map(function (header) {
            return (
              <Table.Row>
                <Table.Cell width={4}>{header.key}</Table.Cell>
                <Table.Cell>{header.value}</Table.Cell>
              </Table.Row>
            );
          })
        );
      }

      // Show attributes
      // TODO: How do we use a custom Semantic UI Toggle checkbox? Can't figure it out with react-hook-form
      if (resJson?.attributes) {
        setAttributes(
          resJson.attributes.map(function (attribute) {
            if (attribute.type === "bool") {
              return (
                <Form.Field>
                  <Popup
                    trigger={<label>{attribute.friendly_name}</label>}
                    content={attribute.description}
                    position="right center"
                    size="mini"
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
                  <input
                    type="checkbox"
                    defaultChecked={attribute.value}
                    {...register(attribute.name)}
                  />
                </Form.Field>
              );
            } else if (attribute.type === "array") {
              return (
                <p>
                  <Popup
                    trigger={<label>{attribute.friendly_name}</label>}
                    content={attribute.description}
                    position="top center"
                    size="mini"
                  />

                  <input
                    defaultValue={attribute.value}
                    {...register(attribute.name)}
                  />
                </p>
              );
            } else {
              return null;
            }
          })
        );
        console.log(attributes);
      }
    }
    fetchDetails();
  }, [sendRequestCommon]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    console.log(userDetails);
  }, [userDetails]);

  return (
    <>
      <Header as="h3">User Details</Header>
      <Table celled striped definition>
        {header}
      </Table>

      <Header as="h3">Add Group Memberships</Header>
      {/* Bulk Add / Bulk Remove groups */}
      {/* TODO: Implement multi-select table  to allow deleting multiple groups at once */}
      {errorMessage ? (
        <Message negative>
          <p>{errorMessage}</p>
        </Message>
      ) : null}
      {statusMessage ? (
        <Message positive>
          <p>{statusMessage}</p>
        </Message>
      ) : null}
      <Form>
        <TextArea
          placeholder="Comma or Newline-Separated List of Groups"
          onChange={(e) => {
            setBulkGroupEditField(e.target.value);
          }}
        />
        <br />
        <br />
        <Form.Field>
          <Header as="h1">
            <Header.Subheader>Justification</Header.Subheader>
          </Header>
          <TextArea
            placeholder="Reason for requesting access"
            onChange={(e) => {
              setJustification(e.target.value);
            }}
          />
        </Form.Field>
        <Form.Field>
          <Header as="h1">
            <Header.Subheader>(Optional) Expiration</Header.Subheader>
          </Header>
          <SemanticDatepicker
            filterDate={(date) => {
              const now = new Date();
              return date >= now;
            }}
            onChange={(e, data) => {
              if (!data?.value) {
                setGroupExpiration(null);
                return;
              }
              const dateObj = DateTime.fromJSDate(data.value);
              const dateString = dateObj.toFormat("yyyyMMdd");
              setGroupExpiration(parseInt(dateString));
            }}
            type="basic"
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
          content={"Add Groups"}
          onClick={handleAddGroups}
          style={{
            width: "50%",
            display: "inline-block",
            textAlign: "center",
            maxWidth: "20em",
          }}
          floated={"right"}
          color={"green"}
        />
      </Form>
      <Header as="h3">Group Memberships</Header>
      <Table celled striped>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>Group Name</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {userDetails?.user?.groups?.map((group) => (
            <Table.Row>
              <Table.Cell>{group}</Table.Cell>
              <Table.Cell>
                <Button color={"orange"} icon labelPosition="right">
                  Remove
                  <Icon name="delete" />
                </Button>
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </>
  );
};

export default IdentityUserEdit;
