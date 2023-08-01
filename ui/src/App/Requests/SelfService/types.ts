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
  url?: string;
  endpoint: string;
  query_param_key: string;
}

export interface ChangeTypeField {
  id: string;
  change_type_id: string;
  change_element: number;
  field_key: string;
  field_value: string;
  field_type: ChangeTypeFieldType;
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
  provider_definition_field?: ProviderDefinitionField;
  included_providers: ProviderDefinition[];
}

export interface IRequest {
  provider: string;
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

export type ChangeTypeItem = {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
  provider_definition_field?: ProviderDefinitionField;
  fields: {
    id: string;
    change_type_id: string;
    change_element: number;
    field_key: string;
    field_type: string;
    field_text: string;
    description: string;
    allow_none: boolean;
    allow_multiple: boolean;
    options?: string[];
    typeahead: {
      endpoint: string;
      query_param_key: string;
    };
    default_value?: any;
    max_char?: number;
    validation_regex?: string;
  };
  included_providers?: any[];
};

export type ProviderDefinitionField =
  | 'Allow Multiple'
  | 'Allow One'
  | 'Allow None';

export type RequestStatus =
  | 'Pending'
  | 'Approved'
  | 'Rejected'
  | 'Expired'
  | 'Running'
  | 'Failed'
  | 'Pending in Git';

export type ChangeTypeFieldType =
  | 'TypeAheadTemplateRef'
  | 'TypeAhead'
  | 'TextBox'
  | 'Choice';

export interface Request {
  id: string;
  repo_name: string;
  pull_request_id: number;
  status: RequestStatus;
  allowed_approvers?: string[] | null;
  created_at: number;
  created_by: string;
  pull_request_url: string;
  updated_at: string;
}

export interface RequestItem {
  pull_request_id: number;
  pull_request_url: string;
  request_id: string;
  requested_by: string;
  title: string;
  description: string;
  comments?: any[];
  files?: FilesEntity[];
  mergeable: boolean;
  merge_on_approval: boolean;
  merged_at?: null;
  closed_at?: null;
  tenant: string;
  repo_name: string;
  justification?: null;
  status: RequestStatus;
  approved_by?: any[];
  rejected_by?: any;
  requested_at?: string;
  updated_at?: string;
  id: string;
  allowed_approvers?: string[] | null;
  created_at: number;
  created_by: string;
}
export interface FilesEntity {
  file_path: string;
  status: string;
  additions: number;
  template_body: string;
  previous_body: string;
}
