// Function to measure the width of text
export const measureTextWidth = text => {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  context.font = '18px sans-serif';
  return context.measureText(text).width;
};

// Function to wrap text to fit within a specified width
export const wrapText = (text, maxWidth, maxHeight) => {
  const words = text.split(' ');
  let lines = [];
  let currentLine = words[0];

  for (let i = 1; i < words.length; i++) {
    const testLine = currentLine + ' ' + words[i];
    const testWidth = measureTextWidth(testLine);

    if (testWidth <= maxWidth && lines.length * 24 <= maxHeight) {
      currentLine = testLine;
    } else {
      lines.push(currentLine);
      currentLine = words[i];
    }
  }
  lines.push(currentLine);
  return lines;
};
