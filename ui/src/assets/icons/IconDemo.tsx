import React, { Suspense } from 'react';

export const iconPaths = import.meta.glob('./*.svg');

export const icons = Object.keys(iconPaths).map(key => ({
  title: key.replace('.svg', '').replace('./', ''),
  component: React.lazy(async () => {
    const lazy: any = await iconPaths[key]();
    return { default: lazy.ReactComponent };
  })
}));


// eslint-disable-next-line react/prop-types
export const IconDemo = ({ component: Component, title }) => (
  <div
    key={title}
    style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '10px',
      background: 'black',
      color: '#898A8E',
      textAlign: 'center',
      fontSize: '12px',
      borderRadius: 10,
      height: 75
    }}
  >
    <Suspense>
      <Component
        style={{ width: 25, height: 25 }}
      />
      <div>{title}</div>
    </Suspense>
  </div>
);
