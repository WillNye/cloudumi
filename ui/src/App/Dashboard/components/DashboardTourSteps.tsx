import { Step } from 'react-joyride';

export const tourSteps: Step[] = [
  {
    content: <h2>Welcome to NOQ</h2>,
    locale: { skip: <strong aria-label="skip">S-K-I-P</strong> },
    placement: 'center',
    target: 'body',
    title: 'welcome'
  },
  {
    content: <h2>Sticky elements</h2>,
    floaterProps: {
      disableAnimation: true
    },
    spotlightPadding: 20,
    placement: 'center',
    target: 'body'
  },
  {
    content: 'These are our super awesome projects!',
    // placement: 'bottom',
    styles: {
      options: {
        width: 300
      }
    },
    placement: 'center',
    target: 'body',
    title: 'Our projects'
  },
  {
    content: (
      <div>
        You can render anything!
        <br />
        <h3>Like this H3 title</h3>
      </div>
    ),
    placement: 'center',
    target: 'body',
    title: 'Our Mission'
  },
  {
    content: (
      <div>
        <h3>All about us</h3>
      </div>
    ),
    placement: 'center',
    target: 'body'
  }
];
