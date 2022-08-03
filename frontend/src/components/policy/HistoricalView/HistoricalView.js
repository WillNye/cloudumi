import { useAuth } from 'auth/AuthProviderDefault'
import { isArray } from 'lodash'
import React, { useCallback, useEffect, useState } from 'react'
import { usePolicyContext } from '../hooks/PolicyProvider'
import DiffEditorBlock from './components/DiffEditorBlock'
import VerticalStepper from './components/VerticalStepper'
import { getNewDiffChanges } from './utils'
import './HistoricalView.scss'

const HistoricalView = () => {
  const { resource = {} } = usePolicyContext()

  const [resourceHistory, setResourceHistory] = useState([])
  const [diffChanges, setDiffChanges] = useState({
    newVersion: null,
    oldVersion: null,
  })

  const { sendRequestCommon } = useAuth()

  const getResourceHistory = async () => {
    const res = await sendRequestCommon(
      null,
      `/api/v3/resource/history/${resource.arn}`,
      'get'
    )
    if (!res) {
      return
    }

    const data = res.data
    if (isArray(data) && data.length) {
      setResourceHistory(res.data)
      setDiffChanges({
        newVersion: res.data[0],
        oldVersion: null,
      })
    }
  }

  useEffect(() => {
    getResourceHistory().then()
  }, []) // eslint-disable-line

  const handleVersionChange = useCallback(
    (version) => {
      setDiffChanges(getNewDiffChanges(diffChanges, version))
    },
    [diffChanges]
  )

  return (
    <div className='historical-view'>
      <VerticalStepper
        resourceHistory={resourceHistory}
        handleVersionChange={handleVersionChange}
        resourceArn={resource.arn}
      />
      <DiffEditorBlock diffChanges={diffChanges} />
    </div>
  )
}

export default HistoricalView
