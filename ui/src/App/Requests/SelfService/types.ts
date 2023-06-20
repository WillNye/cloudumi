export interface RequestType {
  id: string;
  name: string;
  description: string;
  provider: string;
  supported_template_types: string[];
}

export interface Identity {
  id: string;
  resource_id: string;
  resource_type: string;
  template_type: string;
  provider: string;
}

export interface ChangeType {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
}

interface Typeahead {
  url: string;
  query_param_key: string;
}

export interface ChangeTypeField {
  id: string;
  change_type_id: string;
  change_element: number;
  field_key: string;
  field_value: string;
  field_type: string;
  field_text: string;
  description: string;
  allow_none: boolean;
  allow_multiple: boolean;
  options?: string[];
  typeahead?: Typeahead;
  default_value?: any;
  max_char?: number;
  validation_regex?: string;
}

export interface ProviderDefinition {
  id: string;
  name: string;
  provider: string;
  definition: {
    account_id: string;
    account_name: string;
    variables: Array<{ key: string; value: string }>;
    org_id: string;
    preferred_identifier: string;
    all_identifiers: string[];
  };
}

export interface ChangeTypeDetails {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
  fields: ChangeTypeField[];
  included_providers: ProviderDefinition[];
}

export interface IRequest {
  provider: string;
  requestTypes: RequestType[] | [];
  requestType: RequestType | null;
  changeType: ChangeType | null;
  identityType: string | null;
  identity: Identity | null;
  requestedChanges: ChangeTypeDetails[] | [];
  justification: string | null;
  expirationDate: string | null;
}

export interface SubmittableRequest {
  iambic_template_id: string;
  file_path: string | null;
  justification: string;
  template_body: string | null;
  template: string | null;
  expires_at: string;
  changes: {
    change_type_id: string;
    provider_definition_ids: string[];
    fields: {
      field_key: string;
      field_value: string | string[];
    }[];
  }[];
}

export interface TemplatePreviewRequestData {
  iambic_template_id: string;
  justification: string;
  template_body: string;
}

export interface TemplatePreview {
  current_template_body: string;
  request_data: TemplatePreviewRequestData;
}
