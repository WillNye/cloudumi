import { IntegrationSSO } from '../IntegrationSSO'
import { GeneralUsers } from '../GeneralUsers'
import { ServiceAWS } from '../ServiceAWS'
import { IntegrationSlack } from '../IntegrationSlack'

export const services = [
  {
    name: 'aws',
    label: 'AWS',
    Component: ServiceAWS,
  },
]

export const general = [
  {
    name: 'sso',
    label: 'Single Sign-On',
    Component: IntegrationSSO,
  },
  {
    name: 'slack',
    label: 'Slack',
    Component: IntegrationSlack,
  },
  {
    name: 'users',
    label: 'Users and Groups',
    Component: GeneralUsers,
  },
]
