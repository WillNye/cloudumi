import { IRequest, SubmittableRequest } from '../../types';

export const convertToSubmittableRequest = (
  request: IRequest
): SubmittableRequest => {
  const changes = request.requestedChanges.map(change => {
    const fields = change.fields.map(field => ({
      field_key: field.field_key,
      field_value: field.value
    }));

    const providerDefinitionIds = change.included_providers.map(
      provider => provider.id
    );

    return {
      change_type_id: change.id,
      // The provider_definition_ids are unclear from the request, for now returning an empty array
      provider_definition_ids: providerDefinitionIds,
      fields: fields
    };
  });

  console.log('++++++++++++++++++++++++++', request, '+++++++++++++++++');

  return {
    iambic_template_id:
      '0f4deceb-a24a-4497-8b80-0a9c466c13fc' || request.identity?.id || '',
    file_path: null,
    justification: request.justification || '',
    template_body: null,
    template: null,
    expires_at: request.expirationDate || '',
    changes: changes
  };
};
