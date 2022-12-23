import { FC } from 'react';
import ReactQRCode from 'react-qr-code';

interface QRCodeProps {
  value: string;
  size?: number;
  bgColor?: string;
  fgColor?: string;
}

export const QRCode: FC<QRCodeProps> = ({
  bgColor = '#000',
  fgColor = '#fff',
  size = 125,
  value
}) => (
  <ReactQRCode value={value} size={size} bgColor={bgColor} fgColor={fgColor} />
);
