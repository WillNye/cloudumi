/// <reference types="cypress" />
import * as CryptoJS from 'crypto-js';

const DOMAIN = 'test-RANDOM_DIGITS.staging.noq.dev';

const generateRandomDigits = (): string => {
  return Math.floor(1000 + Math.random() * 9000).toString();
};

const generateRandomDomain = (randomDigits: string): string => {
  return DOMAIN.replace('RANDOM_DIGITS', randomDigits);
};

const generateRandomEmail = (randomDigits: string): string => {
  return `cypress_ui_saas_functional_tests+${randomDigits}@noq.dev`;
};

const createTenantPayload = (domain: string, email: string) => {
  const registration_code = CryptoJS.SHA256(`noq_tenant_${email}`)
    .toString(CryptoJS.enc.Hex)
    .substring(0, 20);

  return {
    first_name: 'Functional',
    last_name: 'Test',
    email,
    country: 'USA',
    marketing_consent: true,
    registration_code,
    domain
  };
};

describe('Tenant registration and login', () => {
  const randomDigits = generateRandomDigits();
  const domain = generateRandomDomain(randomDigits);
  const email = generateRandomEmail(randomDigits);
  const payload = createTenantPayload(domain, email);

  after(() => {
    cy.request({
      method: 'DELETE',
      url: 'http://localhost:8092/api/v3/tenant_registration',
      body: {
        email,
        domain
      }
    }).then(response => {
      expect(response.status).to.eq(200);
      expect(response.body.success).to.eq(true);
    });
  });

  it('Should create a new tenant and log in successfully', () => {
    cy.request({
      method: 'POST',
      url: 'http://localhost:8092/api/v3/tenant_registration',
      body: payload
    }).then(response => {
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('domain', 'https://' + domain);

      // Get the password from the response body
      const password = response.body.password;

      // Log in as admin for new tenant
      cy.request({
        method: 'POST',
        url: 'http://localhost:8092/api/v4/users/login',
        body: {
          email: email,
          password: password
        },
        headers: {
          Host: domain
        }
      }).then(loginResponse => {
        expect(loginResponse.status).to.eq(200);
      });
    });
  });
});
