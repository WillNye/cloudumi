export interface RequestType {
  id: string;
  name: string;
  description: string;
  provider: string;
  supported_template_types: string[];
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

export interface ChangeTypeDetails {
  id: string;
  name: string;
  description: string;
  request_type_id: string;
  fields: ChangeTypeField[];
}

export interface IRequest {
  provider: string;
  requestType: RequestType | null;
  changeType: ChangeType | null;
  justification: string | null;
  expirationDate: string | null;
}
