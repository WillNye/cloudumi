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
    user: 'user',
    groups: 'groups',
    email: 'email'
  },
  idp_metadata_url: '',
  sp: {
    entityId: '',
    assertionConsumerService: {
      binding: '',
      url: ''
    }
  },
  idp: {
    entityId: '',
    singleSignOnService: {
      binding: '',
      url: ''
    },
    singleLogoutService: {
      binding: '',
      url: ''
    },
    x509cert: ''
  }
};

export const samlSchema = Yup.object().shape({
  idp_metadata_url: Yup.string().url().default('').label('IDP Metadata URL'),
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
  idp: Yup.object().when('idp_metadata_url', {
    is: (idp_metadata_url: string) => !idp_metadata_url,
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
              url: Yup.string()
                .url()
                .required()
                .label('IDP Single Logout Service URL')
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
