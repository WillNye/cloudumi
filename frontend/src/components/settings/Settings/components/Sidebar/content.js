import { ServiceAWS } from '../ServiceAWS';

export const services = [{
  name: 'aws',
  label: 'AWS',
  Component: ServiceAWS
}, {
  name: 'jira',
  label: 'Jira'
}, {
  name: 'service-now',
  label: 'Service Now'
}, {
  name: 'pagerduty',
  label: 'Pagerduty'
}, {
  name: 'git',
  label: 'Git'
}];

export const general = [{
  name: 'sso',
  label: 'Single Sign-On'
}, {
  name: 'users',
  label: 'Users and Groups'
}, {
  name: 'integrations',
  label: 'Integrations'
}];