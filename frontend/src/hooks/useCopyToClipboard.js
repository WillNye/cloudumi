import { copyToClipboard } from 'helpers/utils'
import React, { useState } from 'react'
import { Button } from 'semantic-ui-react'

export const useCopyToClipboard = () => {
  const [isCopied, setCopied] = useState(false)

  const Component = ({ value, onCopy }) => (
    <Button
      color={isCopied ? 'grey' : 'black'}
      onClick={() => {
        copyToClipboard(value)
        setCopied(true)
        if (onCopy && typeof onCopy === 'function') onCopy()
      }}
      style={{ whiteSpace: 'nowrap', width: 140 }}
    >
      {isCopied ? 'URL Copied!' : 'Copy URL'}
    </Button>
  )

  return {
    CopyButton: Component,
  }
}
