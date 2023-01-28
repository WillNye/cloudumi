import React, { Suspense, useMemo } from 'react';
import styles from './Icon.module.css';

const iconPaths = import.meta.glob('../../../assets/icons/*.svg');

const iconMap = Object.keys(iconPaths).reduce((pathMap, iconPath) => {
  const key = iconPath
    .replace('.svg', '')
    .replace('../../../assets/icons/', '');
  pathMap[key] = React.lazy(async () => {
    const lazy: any = await iconPaths[iconPath]();
    return { default: lazy.ReactComponent };
  });
  return pathMap;
}, {});

export interface IconProps extends React.SVGAttributes<HTMLOrSVGElement> {
  size?: 'small' | 'medium' | 'large';
}

const ICON_SIZES = {
  small: {
    width: 12,
    height: 12
  },
  medium: {
    width: 14,
    height: 14
  },
  large: {
    width: 20,
    height: 20
  }
};

export const Icon: React.FC<IconProps> = ({
  name,
  className,
  size,
  width,
  height,
  ...rest
}) => {
  const SVGIcon = useMemo(() => iconMap[name], [name]);

  const iconSizes = useMemo(() => {
    if (size) {
      return ICON_SIZES[size];
    }

    return {
      width: width ?? ICON_SIZES.small.width,
      height: height ?? ICON_SIZES.small.height
    };
  }, [size, width, height]);

  if (!SVGIcon) {
    return <span></span>;
  }

  return (
    <span className={styles.icon}>
      <Suspense fallback={null}>
        <SVGIcon {...rest} width={iconSizes.width} height={iconSizes.height} />
      </Suspense>
    </span>
  );
};
