## Local Development

For local development, you likely want to iterate using your own Github Apps (still owned by Noq org).
You can click on this [link](https://github.com/organizations/noqdev/settings/apps/new?name=noq-username&description=cloudumi-github-integration&url=https%3A%2F%2Fnoq.dev%2F&setup_url=https%3A%2F%2Fnoq-username.loca.lt%2Fapi%2Fv3%2Fgithub%2Fcallback%2F&webhook_active=true&webhook_url=https%3A%2F%2Fnoq-username.loca.lt%2Fapi%2Fv3%2Fgithub%2Fevents%2F&events[]=meta&events[]=issue_comment&events[]=pull_request_review&events[]=pull_request&events[]=push&public=true&contents=write&pull_requests=write&issues=write) to create your own GitHub App, you will have to modify the name of the app
because name is global across GitHub App and replace noq-username with noq-steven for example to match
your own local tunnel URL.

## The generate_updated_iambic_template function

The generate_updated_iambic_template function is the main function that is called when a self-service request is opened or updated.
It is responsible for rendering an array of user submitted change type values to the change type template and merging the change type templates into an IAMbic template.

### The flow

1. An IAMbic template instance is created using the template content
2. Handle Permission Sets
   - Permission sets are a special case because they only support a single provider definition that can't be easily resolved
   - So, in order to leverage that provider definition in TemplateReference fields we need to load it manually
3. Build out data mappings
   - To reduce the number of look-ups we make we load out certain data ahead of time. This includes:
   - A mapping of relevant change types
   - A mapping of referenced IAMbic template ids
   - A list of provider definition ids across all change types
   - A mapping of provider definitions using the list as mentioned above
4. From this point we explode out each change types provider definition ids, rendering each provider definition + change type separately
   - This is because the value for one provider definition may be different from another
   - For example, `form.role.provider.name` if the template name is `{{var.account_name}}_engineering` this value will be different for each account
5. Render the change type template for a provider definition + change type
   - `render_change_type_template`
   - Iterate the user submitted field values to build out the jinja template attrs
     - This is done by calling `get_field_value`
   - `get_field_value` will perform field validation as specified by the field definition. Included Checks:
     - allow_none
     - allow_multiple
     - max_char
     - validation_regex
     - `TypeAheadTemplateRef` If the referenced template is on the given provider definition
   - `get_field_value` is also responsible for converting a template reference to the proper IAMbic template
     - To create an instance of the referenced template using the provider specific
       - We load the IAMbic provider for the provider definition using `provider_definition.loaded_iambic_provider()`
       - Call `apply_resource_dict` for the generic IAMbic Template instance
       - Use that and other attributes of the generic instance to build out the provider specific values as a dict
       - Load the policy doc for `AwsIamManagedPolicyTemplate` because it's an outlier where apply_resource_dict will convert the dict to str
       - Then finally create a new instance of the template using only the provider values by calling `iambic_template_ref.__class__`
       - The provider specific IAMbic template is then used as the `form_value`
   - Once the form_value has been set it is sanitized then returned to be used in the jinja template
6. Merge the rendered change types into an EnrichedChangeType (`templatize_and_merge_rendered_change_types`)
   - Works by building out a mapping where the key is the change type id and the value is a list of all templatized rendered change types
     - A templatized rendered change type is a rendered change type where the values are replaced with IAMbic provider variables
       - For example, `0123456789` would be replaced with `{{var.account_id}}`
     - This works by calling `templatize_resource`
     - Once we have the templatized rendered change types we remove duplicate values and return a list of unique templatized rendered change types
7. Next, we iterate the templatized change types which are at this point is a dict that is simply an attribute in the IAMbic template
   - Apply the expires_at and included_accounts attrs (if applicable)
   - Call `update_iambic_template_with_change` to set merge the templatized change type into the IAMbic template
     - `update_iambic_template_with_change` is a recursive function that will resolve the field type
     - Once the correct field is determined the value is set but the way it is set is dictated by the `apply_attr_behavior`
       - For information on how each type behaves see the docstring under the `ApplyAttrBehavior` class
       - Quick note: At the time this was written Merge and Replace are not yet supported
     - After the value has been set the IAMbic template is returned
8. And that's it. Now the IAMbic template has been updated with the user submitted values and is returned to the calling function.
