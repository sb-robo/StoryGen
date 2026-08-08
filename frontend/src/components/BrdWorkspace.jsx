import { useCallback, useMemo, useState } from 'react'
import * as brdApi from '../api/brds'
import { useJobs } from '../context/JobsContext'
import { useBrdPipeline } from '../hooks/useBrdPipeline'
import { useReviewQueueShortcuts } from '../hooks/useReviewQueueShortcuts'
import { runBatchAction } from '../utils/batchActions'
import { getBatchActions, getBlockers, getSuggestedStep, ITEM_TYPES } from '../utils/pipeline'
import { approveQueueItem, approveQueueItems, queueItemKey } from '../utils/reviewActions'
import { DetailPanel } from './DetailPanel'
import { OverviewTab } from './OverviewTab'
import { ParsedContentModal } from './ParsedContentModal'
import { PipelineStepper } from './PipelineStepper'
import { ReviewQueue } from './ReviewQueue'
import { StatusBadge } from './StatusBadge'
import { TreeSidebar } from './TreeSidebar'

export function BrdWorkspace({ brd, onRefreshBrd }) {
  const brdId = brd.id
  const { trackJob, jobs } = useJobs()
  const {
    features,
    subFeatures,
    stories,
    testCases,
    parents,
    pipeline,
    reviewQueue,
    loading,
    error: pipelineError,
    reload,
  } = useBrdPipeline(brdId, brd.status)
  const [selectedItem, setSelectedItem] = useState(null)
  const [queueFilter, setQueueFilter] = useState('all')
  const [parentFilter, setParentFilter] = useState('all')
  const [activeStage, setActiveStage] = useState('features')
  const [busy, setBusy] = useState(false)
  const [showContentModal, setShowContentModal] = useState(false)
  const [fullContent, setFullContent] = useState(null)
  const [loadingFullContent, setLoadingFullContent] = useState(false)
  const [workspaceTab, setWorkspaceTab] = useState('overview')
  const [treeOpen, setTreeOpen] = useState(true)
  const [trackedBrdId, setTrackedBrdId] = useState(brdId)
  const [autoSelectedForBrdId, setAutoSelectedForBrdId] = useState(null)
  const [bulkStatus, setBulkStatus] = useState(null)

  // Reset selection when navigating to a different BRD, and auto-select the
  // first feature the first time features become available for a BRD, so the
  // user always lands on something useful beside the tree instead of a blank panel.
  if (trackedBrdId !== brdId) {
    setTrackedBrdId(brdId)
    setSelectedItem(null)
    setFullContent(null)
  } else if (autoSelectedForBrdId !== brdId && features && features.length > 0) {
    setAutoSelectedForBrdId(brdId)
    if (!selectedItem) {
      const first = features[0]
      setSelectedItem({
        id: first.id,
        type: ITEM_TYPES.FEATURE,
        title: first.title,
        parentLabel: '—',
        confidence: first.confidence ?? null,
        status: first.status,
        entity: first,
      })
    }
  }

  const blockers = useMemo(() => getBlockers(features ?? []), [features])
  const suggestedStep = useMemo(
    () => getSuggestedStep({ brdStatus: brd.status, pipeline, reviewQueue }),
    [brd.status, pipeline, reviewQueue],
  )
  const batchActions = useMemo(
    () => (pipeline ? getBatchActions({ pipeline, features: features ?? [], subFeatures: subFeatures ?? [], stories: stories ?? [] }) : []),
    [pipeline, features, subFeatures, stories],
  )
  const recentJobs = useMemo(
    () => jobs.filter((j) => j.brdId === brdId || j.brdId == null).slice(0, 5),
    [jobs, brdId],
  )

  async function refreshAll() {
    await reload()
    await onRefreshBrd?.()
  }

  async function handleViewFullContent() {
    setShowContentModal(true)
    if (brd.parsed_text != null || fullContent != null) return
    setLoadingFullContent(true)
    try {
      const full = await brdApi.getBrd(brdId, true)
      setFullContent(full.parsed_text ?? '')
    } catch {
      setFullContent('Failed to load full content. Please try again.')
    } finally {
      setLoadingFullContent(false)
    }
  }

  async function runJob(label, fn) {
    setBusy(true)
    try {
      const op = await fn()
      await trackJob(op, { label, brdId, onComplete: refreshAll })
      await refreshAll()
    } finally {
      setBusy(false)
    }
  }

  async function handleRunJob(label, fn) {
    await runJob(label, fn)
  }

  async function handleExport(format = 'csv') {
    setBusy(true)
    try {
      if (format === 'jira') await brdApi.exportBrdJira(brdId)
      else await brdApi.exportBrdCsv(brdId)
    } finally {
      setBusy(false)
    }
  }

  async function handleExportCsv() {
    await handleExport('csv')
  }

  const handleApproveItem = useCallback(
    async (item) => {
      if (!item) return
      setBusy(true)
      setBulkStatus(null)
      try {
        await approveQueueItem(item)
        setSelectedItem((current) =>
          queueItemKey(current) === queueItemKey(item) ? null : current,
        )
        await reload()
        await onRefreshBrd?.()
      } catch (err) {
        setBulkStatus({
          failed: 1,
          message: err?.message || 'Approve failed',
        })
      } finally {
        setBusy(false)
      }
    },
    [reload, onRefreshBrd],
  )

  async function handleBulkApprove(items) {
    if (!items?.length || busy) return
    setBusy(true)
    setBulkStatus(null)
    try {
      const { ok, failed } = await approveQueueItems(items)
      const failedKeys = new Set(failed.map((f) => queueItemKey(f.item)))
      setSelectedItem((current) => {
        const selectedKey = queueItemKey(current)
        if (!selectedKey) return current
        const wasTargeted = items.some((item) => queueItemKey(item) === selectedKey)
        if (wasTargeted && !failedKeys.has(selectedKey)) return null
        return current
      })
      if (failed.length === 0) {
        setBulkStatus({ failed: 0, message: `Approved ${ok} item${ok !== 1 ? 's' : ''}.` })
      } else {
        setBulkStatus({
          failed: failed.length,
          message: `Approved ${ok}, failed ${failed.length}: ${failed.map((f) => f.item.title).join(', ')}`,
        })
      }
      await refreshAll()
    } finally {
      setBusy(false)
    }
  }

  useReviewQueueShortcuts({
    enabled: workspaceTab === 'queue' && brd.status === 'parsed',
    items: reviewQueue,
    typeFilter: queueFilter,
    parentFilter,
    selectedItem,
    onSelect: setSelectedItem,
    onApprove: handleApproveItem,
    busy: busy || loading,
  })

  async function handleBatchAction(actionId) {
    if (actionId === 'export_csv') {
      await handleExport('csv')
      return
    }
    if (actionId === 'export_jira') {
      await handleExport('jira')
      return
    }
    setBusy(true)
    try {
      await runBatchAction(actionId, {
        brdId,
        features: features ?? [],
        runJob,
      })
      await refreshAll()
    } finally {
      setBusy(false)
    }
  }

  async function handlePrimaryAction(stageId) {
    setActiveStage(stageId)

    if (stageId === 'features') {
      const featurePending = pipeline?.stages.features.pending ?? 0
      if (featurePending > 0) {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'feature') ?? reviewQueue[0]
        if (first) setSelectedItem(first)
      } else {
        await handleBatchAction('extract_features')
      }
      return
    }

    if (stageId === 'sub_features') {
      if (pipeline?.stages.sub_features.counts?.total === 0) {
        await handleBatchAction('batch_sub_features')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'sub_feature')
        if (first) setSelectedItem(first)
      }
      return
    }

    if (stageId === 'stories') {
      if (pipeline?.stages.stories.counts?.total === 0) {
        await handleBatchAction('batch_stories')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'story')
        if (first) setSelectedItem(first)
      }
      return
    }

    if (stageId === 'tests') {
      if (pipeline?.stages.tests.counts?.total === 0) {
        await handleBatchAction('batch_tests')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'test_case')
        if (first) setSelectedItem(first)
      }
      return
    }

    if (stageId === 'points') {
      if (pipeline?.stages.points.status === 'not_started') {
        await handleBatchAction('batch_points')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'points')
        if (first) setSelectedItem(first)
      }
      return
    }

    if (stageId === 'export') {
      await handleExportCsv()
    }
  }

  function handleSuggestedAction(step) {
    if (step.action === 'review') {
      setWorkspaceTab('queue')
      if (reviewQueue[0]) setSelectedItem(reviewQueue[0])
      return
    }
    if (step.action === 'export_csv' || step.action === 'export_jira') {
      handleExport(step.action === 'export_jira' ? 'jira' : 'csv')
      return
    }
    if (step.action) {
      handleBatchAction(step.action)
    }
  }

  function handleStageClick(stageId) {
    setActiveStage(stageId)
    if (stageId === 'features' || stageId === 'sub_features' || stageId === 'stories' || stageId === 'points' || stageId === 'tests') {
      setWorkspaceTab('queue')
    }
  }

  const brdReady = brd.status === 'parsed'
  const detailInMiddle = workspaceTab === 'overview' && !!selectedItem

  return (
    <div className="brd-workspace">
      <div className="workspace-header">
        <div className="brd-meta">
          <StatusBadge status={brd.status} />
          <span className="meta">{brd.original_filename}</span>
          {reviewQueue.length > 0 && (
            <span className="pending-badge">{reviewQueue.length} pending review</span>
          )}
        </div>
      </div>

      {(brd.preview || brd.parsed_text) && (
        <section className="panel parsed-content-panel">
          <div className="parsed-content-header">
            <h3>Parsed BRD content</h3>
            <button type="button" className="btn btn-ghost btn-sm" onClick={handleViewFullContent}>
              View full content
            </button>
          </div>
          {brd.preview && <pre className="content-preview">{brd.preview}</pre>}
        </section>
      )}

      {showContentModal && (
        <ParsedContentModal
          content={brd.parsed_text ?? fullContent}
          loading={loadingFullContent}
          onClose={() => setShowContentModal(false)}
        />
      )}

      <PipelineStepper
        stages={pipeline?.stages}
        activeStage={activeStage}
        onStageClick={handleStageClick}
        onPrimaryAction={handlePrimaryAction}
        busy={busy || loading}
      />

      {!brdReady && (
        <section className="panel workspace-notice">
          <p className="empty-hint">Parse the BRD before running the AI pipeline.</p>
        </section>
      )}

      {brdReady && pipelineError && (
        <section className="panel workspace-notice">
          <p className="form-error">{pipelineError}</p>
          <button type="button" className="btn btn-ghost btn-sm" onClick={reload}>
            Retry
          </button>
        </section>
      )}

      {brdReady && !pipelineError && (
        <>
          {loading && <p className="empty-hint workspace-loading">Loading pipeline data…</p>}

          <div className="workspace-tabs-row">
            <div className="workspace-tabs">
              <button
                type="button"
                className={`workspace-tab ${workspaceTab === 'overview' ? 'workspace-tab-active' : ''}`}
                onClick={() => setWorkspaceTab('overview')}
              >
                Overview
              </button>
              <button
                type="button"
                className={`workspace-tab ${workspaceTab === 'queue' ? 'workspace-tab-active' : ''}`}
                onClick={() => setWorkspaceTab('queue')}
              >
                Review queue
                {reviewQueue.length > 0 && <span className="chip-count">{reviewQueue.length}</span>}
              </button>
            </div>
            <button
              type="button"
              className={`btn btn-ghost btn-sm tree-toggle-btn ${treeOpen ? 'tree-toggle-btn-active' : ''}`}
              onClick={() => setTreeOpen((v) => !v)}
              aria-pressed={treeOpen}
            >
              {treeOpen ? 'Hide structure' : 'Show structure'}
            </button>
          </div>

          <div className={`workspace-split ${detailInMiddle ? 'workspace-split-detail-first' : ''}`}>
            {treeOpen && (
              <TreeSidebar
                features={features ?? []}
                subFeatures={subFeatures ?? []}
                stories={stories ?? []}
                testCases={testCases ?? []}
                selectedItem={selectedItem}
                onSelect={setSelectedItem}
                onClose={() => setTreeOpen(false)}
              />
            )}

            <div className={`workspace-main ${detailInMiddle ? 'workspace-main-compact' : ''}`}>
              {workspaceTab === 'overview' && (
                <OverviewTab
                  pipeline={pipeline}
                  reviewQueue={reviewQueue}
                  blockers={blockers}
                  suggestedStep={suggestedStep}
                  recentJobs={recentJobs}
                  batchActions={batchActions}
                  busy={busy || loading}
                  onGoToQueue={() => {
                    setWorkspaceTab('queue')
                    if (reviewQueue[0]) setSelectedItem(reviewQueue[0])
                  }}
                  onSuggestedAction={handleSuggestedAction}
                  onBatchAction={handleBatchAction}
                />
              )}

              {workspaceTab === 'queue' && (
                <ReviewQueue
                  items={reviewQueue}
                  selectedItem={selectedItem}
                  onSelect={setSelectedItem}
                  filter={queueFilter}
                  onFilterChange={setQueueFilter}
                  parentFilter={parentFilter}
                  onParentFilterChange={setParentFilter}
                  busy={busy || loading}
                  onBulkApprove={handleBulkApprove}
                  bulkStatus={bulkStatus}
                />
              )}
            </div>

            {selectedItem && (
              <DetailPanel
                item={selectedItem}
                busy={busy}
                onClose={() => setSelectedItem(null)}
                onRefresh={refreshAll}
                onSelectItem={setSelectedItem}
                onRunJob={handleRunJob}
                parents={parents}
                wide={detailInMiddle}
              />
            )}
          </div>
        </>
      )}
    </div>
  )
}
