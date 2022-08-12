import { useAuth } from 'auth/AuthProviderDefault'
import { isArray } from 'lodash'
import React, { useCallback, useEffect, useState } from 'react'
import { usePolicyContext } from '../hooks/PolicyProvider'
import DiffEditorBlock from './components/DiffEditorBlock'
import VerticalStepper from './components/VerticalStepper'
import { getNewDiffChanges } from './utils'
import './HistoricalView.scss'

const HistoricalView = () => {
  const { resource = {}, setIsPolicyEditorLoading } = usePolicyContext()

  const [resourceHistory, setResourceHistory] = useState([])
  const [associatedHistoryChange, setAssociatedHistoryChange] = useState(null)
  const [diffChanges, setDiffChanges] = useState({
    newVersion: null,
    oldVersion: null,
  })

  const { sendRequestCommon } = useAuth()

  const getResourceHistory = async () => {
    setIsPolicyEditorLoading(true)
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

    setIsPolicyEditorLoading(false)
  }

  useEffect(() => {
    getResourceHistory().then()
  }, []) // eslint-disable-line

  const handleAssociatedHistoryChange = (newVersion) => {
    setAssociatedHistoryChange(newVersion)
    setDiffChanges({
      newVersion: null,
      oldVersion: null,
    })
  }

  const handleVersionChange = useCallback(
    (version) => {
      const { oldVersion, newVersion } = diffChanges

      setAssociatedHistoryChange(null)

      if (!newVersion) {
        setDiffChanges({ ...diffChanges, newVersion: version })
        return
      }

      if (oldVersion && version.updated_at === oldVersion.updated_at) {
        setDiffChanges({ ...diffChanges, oldVersion: null })
        return
      }

      if (version.updated_at === newVersion.updated_at) {
        if (!oldVersion) return
        setDiffChanges({ oldVersion: null, newVersion: oldVersion })
        return
      }

      setDiffChanges(getNewDiffChanges(diffChanges, version))
    },
    [diffChanges]
  )

  return (
    <div className='historical-view'>
      {resourceHistory.length ? (
        <>
          <VerticalStepper
            resourceHistory={resourceHistory}
            handleVersionChange={handleVersionChange}
            handleAssociatedHistoryChange={handleAssociatedHistoryChange}
            resourceArn={resource.arn}
            diffChanges={diffChanges}
            associatedHistoryChange={associatedHistoryChange}
          />
          <DiffEditorBlock
            diffChanges={diffChanges}
            associatedHistoryChange={associatedHistoryChange}
          />
        </>
      ) : (
        <div className='historical-view__not-found'>
          <h4>Resource History</h4>
          <p className='historical-view__not-found__text'>
            No history found for {resource.arn}
          </p>
        </div>
      )}
    </div>
  )
}

export default HistoricalView
