import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Checkbox,
  Divider,
  Header,
  Popup,
  Input,
  Table,
  Form,
  Ref,
} from "semantic-ui-react";
import { useAuth } from "../../auth/AuthProviderDefault";
import { useForm, Controller } from "react-hook-form";

const IdentityGroupEdit = () => {
  const auth = useAuth();
  const { sendRequestCommon } = auth;
  const { idpName, groupName } = useParams();

  const [header, setHeader] = useState(null);
  const [attributes, setAttributes] = useState(null);
  const [groupDetails, setGroupDetails] = useState(null);
  const {
    control,
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();
  const onSubmit = async (data) => {
    const resJson = await sendRequestCommon(
      data,
      "/api/v3/identities/group/" + idpName + "/" + groupName
    );
    // TODO: Post data and render response message/error in a generic way
    console.log(data);
    //console.log(resJson)
  };

  useEffect(() => {
    async function fetchDetails() {
      const resJson = await sendRequestCommon(
        null,
        "/api/v3/identities/group/" + idpName + "/" + groupName,
        "get"
      );
      if (!resJson) {
        return;
      }
      setGroupDetails(resJson);

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
                  <input type="checkbox" {...register(attribute.name)} />
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
                    // defaultValue={defaultValues.email}
                    {...register(attribute.name)}
                  />
                </p>
              );
            } else {
              return null;
            }
          })
        );
      }
    }
    fetchDetails();
  }, [sendRequestCommon]);

  useEffect(() => {
    console.log(groupDetails);
  }, [groupDetails]);

  return (
    <>
      <Header as="h3">Group Details</Header>
      <Table celled striped definition>
        {header}
      </Table>
      <Header as="h3">Group Attributes</Header>

      <Form onSubmit={handleSubmit(onSubmit)}>
        {attributes}
        <Button primary ype="submit">
          Save
        </Button>
      </Form>
    </>
  );
};

export default IdentityGroupEdit;
