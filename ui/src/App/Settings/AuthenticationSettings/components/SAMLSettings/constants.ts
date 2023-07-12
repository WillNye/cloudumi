import * as Yup from 'yup';

// SAML Bindings: https://en.wikipedia.org/wiki/SAML_2.0#Bindings
export const BINDINGS = [
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST',
  'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
];

export const DEFAULT_SAML_SETTINGS = {
  jwt: {
    expiration_hours: 2,
    email_key: 'email',
    group_key: 'groups'
  },
  attributes: {
    user: 'email',
    groups: 'groups',
    email: 'email'
  },
  use_metadata_url: true,
  idp_metadata_url: '',
  sp: {
    entityId: '',
    assertionConsumerService: {
      binding: BINDINGS[0],
      url: ''
    }
  },
  idp: {
    entityId: '',
    singleSignOnService: {
      binding: BINDINGS[0],
      url: ''
    },
    singleLogoutService: {
      binding: BINDINGS[0],
      url: ''
    },
    x509cert: ''
  }
};

export const samlSchema = Yup.object().shape({
  use_metadata_url: Yup.boolean().default(true),
  idp_metadata_url: Yup.string()
    .url()
    .default('')
    .label('IDP Metadata URL')
    .when('use_metadata_url', { is: true, then: sch => sch.required() }),
  jwt: Yup.object().shape({
    expiration_hours: Yup.number().default(1).label('Expiration Hours'),
    email_key: Yup.string().default('email').label('Email Key'),
    group_key: Yup.string().default('groups').label('Group Key')
  }),
  attributes: Yup.object().shape({
    user: Yup.string().default('user').label('Attribute User'),
    groups: Yup.string().default('groups').label('Attribute Groups'),
    email: Yup.string().default('email').label('Attribute Email')
  }),
  idp: Yup.object().when('use_metadata_url', {
    is: false,
    then: schema =>
      schema
        .shape({
          entityId: Yup.string().required().label('IDP Entity ID'),
          singleSignOnService: Yup.object()
            .shape({
              binding: Yup.string()
                .oneOf(BINDINGS)
                .default(BINDINGS[0])
                .required()
                .label('IDP Single Sign On Service Binding'),
              url: Yup.string()
                .url()
                .required()
                .label('IDP Single Sign On Service URL')
            })
            .notRequired(),
          singleLogoutService: Yup.object()
            .shape({
              binding: Yup.string()
                .oneOf(BINDINGS)
                .default(BINDINGS[0])
                .required()
                .label('IDP Single Logout Service Binding'),
              url: Yup.string().url().label('IDP Single Logout Service URL')
            })
            .notRequired(),
          x509cert: Yup.string().required().label('X509Cert')
        })
        .required(),
    otherwise: schema => schema.notRequired()
  }),
  sp: Yup.object()
    .shape({
      assertionConsumerService: Yup.object().shape({
        binding: Yup.string()
          .oneOf([...BINDINGS, '', null])
          .default('')
          .notRequired()
          .label('SP Assertion Consumer Service Binding'),
        url: Yup.string().url().notRequired()
      }),
      entityId: Yup.string().label('SP Entity ID')
    })
    .notRequired()
});
