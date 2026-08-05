import { useCallback, useEffect, useState } from 'react'
import * as testCaseApi from '../api/testCases'
import * as storyApi from '../api/stories'
import { EditModal } from './EditModal'
import { ReviewActions, ReviewCard } from './ReviewCard'
import { useOperationPoll } from '../hooks/useOperationPoll'
import { OperationBanner } from './OperationBanner'

export function TestCaseSection({ story, onRefresh }) {
  const [testCases, setTestCases] = useState([])
  const [editItem, setEditItem] = useState(null)
  const [busy, setBusy] = useState(false)
  const { operation, error, loading, startPoll } = useOperationPoll()

  const load = useCallback(async () => {
    const data = await storyApi.listTestCases(story.id)
    setTestCases(data.items)
  }, [story.id])

  useEffect(() => {
    load()
  }, [load])

  async function handleGenerate() {
    setBusy(true)
    try {
      const op = await storyApi.generateTestCases(story.id)
      await startPoll(op)
      await load()
      onRefresh?.()
    } finally {
      setBusy(false)
    }
  }

  async function handleReview(id, action) {
    setBusy(true)
    try {
      if (action === 'approve') await testCaseApi.approveTestCase(id)
      else await testCaseApi.rejectTestCase(id)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="nested-section">
      <div className="section-toolbar">
        <h5>Test cases</h5>
        {story.status === 'approved' && (
          <button type="button" className="btn btn-primary btn-sm" onClick={handleGenerate} disabled={busy || loading}>
            Generate test cases
          </button>
        )}
      </div>
      <OperationBanner operation={operation} error={error} loading={loading} />
      {testCases.length === 0 && <p className="empty-hint">No test cases yet.</p>}
      {testCases.map((tc) => (
        <ReviewCard
          key={tc.id}
          title={tc.title}
          description={tc.steps}
          status={tc.status}
          confidence={tc.confidence}
          rationale={tc.rationale}
          extra={
            <p className="meta">
              Type: {tc.test_type} · Expected: {tc.expected_result}
            </p>
          }
          actions={
            tc.status === 'pending_review' ? (
              <ReviewActions
                onApprove={() => handleReview(tc.id, 'approve')}
                onReject={() => handleReview(tc.id, 'reject')}
                onEdit={() => setEditItem(tc)}
                disabled={busy}
              />
            ) : null
          }
        />
      ))}
      {editItem && (
        <EditModal
          title="Edit test case"
          fields={[
            { name: 'title', label: 'Title', value: editItem.title },
            { name: 'steps', label: 'Steps', type: 'textarea', value: editItem.steps },
            { name: 'expected_result', label: 'Expected result', type: 'textarea', value: editItem.expected_result },
            { name: 'test_type', label: 'Type (happy_path / edge_case / negative)', value: editItem.test_type },
          ]}
          onSave={(payload) => testCaseApi.updateTestCase(editItem.id, payload).then(load)}
          onClose={() => setEditItem(null)}
        />
      )}
    </div>
  )
}
