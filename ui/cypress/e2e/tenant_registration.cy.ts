/// <reference types="cypress" />
import * as CryptoJS from 'crypto-js';
import { authenticator } from 'otplib';

const DOMAIN = 'test-RANDOM_DIGITS.example.com';

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

  beforeEach(() => {
    cy.setCookie('V2_UI', 'true');
    cy.intercept('*', req => {
      if (req.url.startsWith(Cypress.config('baseUrl'))) {
        req.headers['Host'] = domain; // Host header won't work with cypress
        req.headers['X-Forwarded-Host'] = domain;
      }
    });
  });

  after(() => {
    cy.request({
      method: 'DELETE',
      url: `${Cypress.config('baseUrl')}/api/v3/tenant_registration`,
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
    defaultCommandTimeout: 15000;
    cy.request({
      method: 'POST',
      url: `${Cypress.config('baseUrl')}/api/v3/tenant_registration`,
      body: payload
    }).then(response => {
      expect(response.status).to.eq(200);
      expect(response.body).to.have.property('domain', 'https://' + domain);

      // Get the password from the response body
      const password = response.body.password;

      // cy.intercept('http://localhost:8092/*', (req) => {
      //   req.headers['Host'] = domain;
      //   req.headers['V2_UI'] = 'true';
      // });
      // Log in as admin for new tenant
      // Visit the login page
      cy.visit({
        url: `${Cypress.config('baseUrl')}`
      });

      // Fill in and submit the login form
      cy.get('input[name="email"]') // Update the selector to match your email input element
        .type(email)
        .should('have.value', email);

      cy.get('input[name="password"]') // Update the selector to match your password input element
        .click()
        .type(password, { force: true })
        .should('have.value', password);

      cy.get('button[type="submit"]') // Update the selector to match your submit button element
        .click();

      // Fill in the current password
      cy.get('input[name="currentPassword"]') // Update the selector to match your current password input element
        .type(password)
        .should('have.value', password);

      // Fill in the new password
      cy.get('input[name="newPassword"]') // Update the selector to match your new password input element
        .type(password)
        .should('have.value', password);

      // Confirm the new password
      cy.get('input[name="confirmNewPassword"]') // Update the selector to match your confirm new password input element
        .type(password)
        .should('have.value', password);

      // Submit the change password form
      cy.get('button[type="submit"]') // Update the selector to match your submit button element on the change password form
        .click();

      // Get the manual TOTP code
      cy.get('[data-testid="manual-code"] pre')
        .invoke('text')
        .then(manualCode => {
          // Generate a valid TOTP key using the manual code
          const totpKey = authenticator.generate(manualCode);

          // Fill in the TOTP key input
          const totpKeyDigits = totpKey.split('');
          totpKeyDigits.forEach((digit, index) => {
            cy.get(
              `input[aria-label="Authentication Code. Character ${index + 1}."]`
            )
              .type(digit)
              .should('have.value', digit);
          });

          cy.contains('Role Access').should('be.visible');
          cy.contains('AWS Console Sign-In').should('be.visible');
          cy.get(
            'input[placeholder="Filter Roles by Account Name, Account ID or Role Name"]'
          ).should('be.visible');
        });
    });
  });
});
