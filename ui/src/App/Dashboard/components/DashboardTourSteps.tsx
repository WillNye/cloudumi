import { Step } from 'react-joyride';
import { theme } from 'shared/utils/DesignTokens';

export const commonTourProps: Partial<Step> = {
  disableBeacon: true,
  disableOverlayClose: true,
  hideCloseButton: true,
  spotlightClicks: true,
  showProgress: false,
  showSkipButton: true,
  placement: 'center',
  styles: {
    options: {
      zIndex: 10000,
      arrowColor: theme.colors.gray[600],
      backgroundColor: theme.colors.gray[600],
      primaryColor: theme.colors.blue[600],
      textColor: theme.colors.white,
      overlayColor: theme.colors.gray[700],
      width: '450px'
    },
    buttonNext: {
      padding: `${theme.spacings.md} ${theme.spacings.lg}`,
      fontSize: theme.typography.sizes.sm,
      userSelect: 'none'
    }
  },
  locale: {
    skip: <strong>SKIP</strong>,
    last: 'Setup'
  }
};

export const tourSteps: Step[] = [
  {
    content: (
      <p>
        Let&apos;s create a secure environment together. Assistance is always
        available if you need it. Let&apos;s get started!
      </p>
    ),
    target: 'body',
    title: 'Welcome to Noq',
    ...commonTourProps
  },
  {
    content: (
      <p>
        To get started with our NOQ, please configure your AWS and GitHub
        settings. This essential step will ensure smooth and secure identity and
        access management across your infrastructure.
      </p>
    ),
    title: 'Onboarding',
    target: 'body',
    ...commonTourProps
  }
];
