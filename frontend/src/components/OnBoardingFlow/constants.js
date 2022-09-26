export const ACCOUNT_NAME_REGEX = new RegExp(/[\s\S]*/)

export const MODES = {
  READ_ONLY: 'read-only',
  READ_WRTE: 'read-write',
}

export const ONBOARDING_SECTIONS = {
  CONNECTION_METHOD: {
    value: 'Connection Method',
    id: 1,
  },
  CONFIGURE: {
    value: 'Configure',
    id: 2,
  },
  CREATE_STACK: {
    value: 'Login to AWS & Create Stack',
    id: 3,
  },
  STATUS: {
    value: 'Status',
    id: 4,
  },
}

const { CONNECTION_METHOD, CONFIGURE, CREATE_STACK, STATUS } =
  ONBOARDING_SECTIONS

export const ONBOARDING_STEPS = [
  {
    id: CONNECTION_METHOD.id,
    header: CONNECTION_METHOD.value,
    subHeader: '',
  },

  {
    id: CONFIGURE.id,
    header: CONFIGURE.value,
    subHeader: '',
  },

  {
    id: CREATE_STACK.id,
    header: CREATE_STACK.value,
    subHeader: '',
  },

  {
    id: STATUS.id,
    header: STATUS.value,
    subHeader: '',
  },
]
