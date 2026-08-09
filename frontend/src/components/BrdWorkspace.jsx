import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import * as brdApi from '../api/brds'
import { useJobs } from '../context/JobsContext'
import { useBrdPipeline } from '../hooks/useBrdPipeline'
import { useReviewQueueShortcuts } from '../hooks/useReviewQueueShortcuts'
import { runBatchAction } from '../utils/batchActions'
import {
  exportReadinessLabel,
  getBatchActions,
  getBlockers,
  getExportReadiness,
  getSuggestedStep,
  ITEM_TYPES,
  regenerateConfirmMessage,
} from '../utils/pipeline'
import {
  hydratePipelineSettings,
  serializePipelineSettings,
} from '../utils/pipelineSettings'
import {
  approveQueueItem,
  approveQueueItems,
  filterReviewQueue,
  nextQueueItem,
  queueItemKey,
  rejectQueueItem,
} from '../utils/reviewActions'
import { resolveJobFocusTarget } from '../utils/jobFocus'
import { ChunkProvenanceModal } from './ChunkProvenanceModal'
import { ConfirmModal } from './ConfirmModal'
import { DetailPanel } from './DetailPanel'
import { ExportReadyModal } from './ExportReadyModal'
import { OverviewTab } from './OverviewTab'
import { ParsedContentModal } from './ParsedContentModal'
import { PipelineSettingsForm } from './PipelineSettingsForm'
import { PipelineStepper } from './PipelineStepper'
import { ReviewQueue } from './ReviewQueue'
import { StatusBadge } from './StatusBadge'
import { TreeSidebar } from './TreeSidebar'

export function BrdWorkspace({ brd, onRefreshBrd }) {
  const brdId = brd.id
  const location = useLocation()
  const navigate = useNavigate()
  const { trackJob, jobs, jobFocus, clearJobFocus } = useJobs()
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
  const [regenConfirm, setRegenConfirm] = useState(null)
  const [exportConfirm, setExportConfirm] = useState(false)
  const [provenance, setProvenance] = useState(null)
  const [pendingSelectKey, setPendingSelectKey] = useState(null)
  const [editRequestKey, setEditRequestKey] = useState(null)
  const [showSettings, setShowSettings] = useState(false)
  const [settings, setSettings] = useState(() => hydratePipelineSettings(brd.pipeline_settings))
  const [settingsStatus, setSettingsStatus] = useState('')
  const [savingSettings, setSavingSettings] = useState(false)
  const [isNarrow, setIsNarrow] = useState(false)

  useEffect(() => {
    setSettings(hydratePipelineSettings(brd.pipeline_settings))
  }, [brd.id, brd.pipeline_settings])

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return undefined
    const mq = window.matchMedia('(max-width: 768px)')
    const apply = () => {
      const narrow = mq.matches
      setIsNarrow(narrow)
      if (narrow) setTreeOpen(false)
    }
    apply()
    mq.addEventListener('change', apply)
    return () => mq.removeEventListener('change', apply)
  }, [])

  const selectItem = useCallback(
    (item) => {
      setSelectedItem(item)
      if (isNarrow) setTreeOpen(false)
    },
    [isNarrow],
  )

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

  // After approve/reject-and-continue, select the next queue item once data reloads.
  // When the queue is empty, stay on Queue and surface the suggested next stage.
  useEffect(() => {
    if (!pendingSelectKey || loading) return
    if (pendingSelectKey === '__none__') {
      setSelectedItem(null)
      setPendingSelectKey(null)
      setWorkspaceTab('queue')
      const next = getSuggestedStep({
        brdStatus: brd.status,
        pipeline,
        reviewQueue,
      })
      if (next?.action && next.action !== 'review') {
        setBulkStatus({
          failed: 0,
          message: `Caught up — next: ${next.label}`,
        })
      } else {
        setBulkStatus({ failed: 0, message: 'Caught up — nothing pending review.' })
      }
      return
    }
    const found = reviewQueue.find((item) => queueItemKey(item) === pendingSelectKey)
    setSelectedItem(found ?? reviewQueue[0] ?? null)
    setPendingSelectKey(null)
    if (found || reviewQueue.length > 0) setWorkspaceTab('queue')
  }, [pendingSelectKey, reviewQueue, loading, brd.status, pipeline])

  // Jobs drawer click-through: focus the affected item when pipeline data is ready.
  useEffect(() => {
    const focus = jobFocus || location.state?.jobFocus
    if (!focus || loading) return
    const targetBrdId = focus.brdId ?? (focus.resourceType === 'brd' ? focus.resourceId : null)
    if (targetBrdId != null && Number(targetBrdId) !== Number(brdId)) return

    const target = resolveJobFocusTarget(focus, {
      features: features ?? [],
      subFeatures: subFeatures ?? [],
      stories: stories ?? [],
      testCases: testCases ?? [],
      reviewQueue,
    })
    if (target.tab) setWorkspaceTab(target.tab)
    if (target.queueFilter) setQueueFilter(target.queueFilter)
    if (target.item) setSelectedItem(target.item)
    clearJobFocus?.()
    if (location.state?.jobFocus) {
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [
    jobFocus,
    location.state,
    location.pathname,
    loading,
    brdId,
    features,
    subFeatures,
    stories,
    testCases,
    reviewQueue,
    clearJobFocus,
    navigate,
  ])

  // Keep the detail panel's entity in sync after approve/reject/reopen reloads.
  useEffect(() => {
    if (pendingSelectKey) return
    if (!selectedItem?.entity) return
    const { type, entity } = selectedItem
    let fresh = null
    if (type === ITEM_TYPES.FEATURE) fresh = (features ?? []).find((f) => f.id === entity.id)
    else if (type === ITEM_TYPES.SUB_FEATURE) {
      fresh = (subFeatures ?? []).find((sf) => sf.id === entity.id)
    } else if (type === ITEM_TYPES.STORY || type === ITEM_TYPES.POINTS) {
      fresh = (stories ?? []).find((s) => s.id === entity.id)
    } else if (type === ITEM_TYPES.TEST_CASE) {
      fresh = (testCases ?? []).find((tc) => tc.id === entity.id)
    }
    if (!fresh) return
    const nextStatus = type === ITEM_TYPES.POINTS ? fresh.points_status : fresh.status
    if (fresh === entity && nextStatus === selectedItem.status) return
    setSelectedItem((current) => {
      if (!current || queueItemKey(current) !== queueItemKey(selectedItem)) return current
      return {
        ...current,
        title: fresh.title,
        status: nextStatus,
        confidence: fresh.confidence ?? null,
        entity: fresh,
      }
    })
  }, [features, subFeatures, stories, testCases, selectedItem, pendingSelectKey])

  const blockers = useMemo(() => getBlockers(features ?? []), [features])
  const exportReadiness = useMemo(
    () => getExportReadiness({ stories: stories ?? [], testCases: testCases ?? [] }),
    [stories, testCases],
  )
  const suggestedStep = useMemo(
    () => getSuggestedStep({ brdStatus: brd.status, pipeline, reviewQueue }),
    [brd.status, pipeline, reviewQueue],
  )
  const batchActions = useMemo(
    () =>
      pipeline
        ? getBatchActions({
            pipeline,
            features: features ?? [],
            subFeatures: subFeatures ?? [],
            stories: stories ?? [],
            testCases: testCases ?? [],
          })
        : [],
    [pipeline, features, subFeatures, stories, testCases],
  )
  const recentJobs = useMemo(
    () => jobs.filter((j) => j.brdId === brdId || j.brdId == null).slice(0, 5),
    [jobs, brdId],
  )

  async function refreshAll() {
    await reload()
    await onRefreshBrd?.()
  }

  async function handleSaveSettings(e) {
    e.preventDefault()
    setSavingSettings(true)
    setSettingsStatus('')
    try {
      const updated = await brdApi.updatePipelineSettings(
        brdId,
        serializePipelineSettings(settings),
      )
      setSettings(hydratePipelineSettings(updated.pipeline_settings))
      setSettingsStatus('Preferences saved. They apply on the next generate/extract run.')
      await onRefreshBrd?.()
    } catch (err) {
      setSettingsStatus(err.message || 'Failed to save preferences')
    } finally {
      setSavingSettings(false)
    }
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
    // Only lock the UI while enqueueing. Tracking/polling must not block
    // generating for other features/sub-features concurrently.
    setBusy(true)
    let op
    try {
      op = await fn()
    } finally {
      setBusy(false)
    }
    void trackJob(op, {
      label,
      brdId,
      onComplete: () => {
        void refreshAll()
      },
    }).catch(() => {
      // Toast/error handled inside JobsContext.trackJob
    })
    return op
  }

  async function handleRunJob(label, fn) {
    return runJob(label, fn)
  }

  async function handleExport(format = 'csv') {
    setBusy(true)
    try {
      if (format === 'jira') await brdApi.exportBrdJira(brdId)
      else if (format === 'markdown') await brdApi.exportBrdMarkdown(brdId)
      else await brdApi.exportBrdCsv(brdId)
      setExportConfirm(false)
    } finally {
      setBusy(false)
    }
  }

  function openExportConfirm() {
    setExportConfirm(true)
  }

  const handleApproveItem = useCallback(
    async (item) => {
      if (!item) return
      const filtered = filterReviewQueue(reviewQueue, queueFilter, parentFilter)
      const next = nextQueueItem(filtered, item)
      setBusy(true)
      setBulkStatus(null)
      try {
        await approveQueueItem(item)
        setPendingSelectKey(next ? queueItemKey(next) : '__none__')
        await reload()
        await onRefreshBrd?.()
      } catch (err) {
        setPendingSelectKey(null)
        setBulkStatus({
          failed: 1,
          message: err?.message || 'Approve failed',
        })
      } finally {
        setBusy(false)
      }
    },
    [reload, onRefreshBrd, reviewQueue, queueFilter, parentFilter],
  )

  const handleRejectItem = useCallback(
    async (item) => {
      if (!item || item.type === ITEM_TYPES.POINTS) return
      const filtered = filterReviewQueue(reviewQueue, queueFilter, parentFilter)
      const next = nextQueueItem(filtered, item)
      setBusy(true)
      setBulkStatus(null)
      try {
        await rejectQueueItem(item)
        setPendingSelectKey(next ? queueItemKey(next) : '__none__')
        await reload()
        await onRefreshBrd?.()
      } catch (err) {
        setPendingSelectKey(null)
        setBulkStatus({
          failed: 1,
          message: err?.message || 'Reject failed',
        })
      } finally {
        setBusy(false)
      }
    },
    [reload, onRefreshBrd, reviewQueue, queueFilter, parentFilter],
  )

  const handleEditItem = useCallback(
    (item) => {
      if (!item || item.type === ITEM_TYPES.POINTS) return
      selectItem(item)
      setEditRequestKey(queueItemKey(item))
    },
    [selectItem],
  )

  async function handleBulkApprove(items) {
    if (!items?.length || busy) return
    setBusy(true)
    setBulkStatus(null)
    try {
      const { ok, failed } = await approveQueueItems(items)
      const failedKeys = new Set(failed.map((f) => queueItemKey(f.item)))
      const nextAfterBulk = items
        .map((item, index) => ({ item, index }))
        .reverse()
        .find(({ item }) => !failedKeys.has(queueItemKey(item)))
      if (nextAfterBulk) {
        const filtered = filterReviewQueue(reviewQueue, queueFilter, parentFilter)
        const next = nextQueueItem(filtered, nextAfterBulk.item)
        setPendingSelectKey(next ? queueItemKey(next) : '__none__')
      }
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
    onSelect: selectItem,
    onApprove: handleApproveItem,
    onReject: handleRejectItem,
    onEdit: handleEditItem,
    busy: busy || loading,
  })

  async function executeBatchAction(actionId) {
    if (
      actionId === 'export_csv' ||
      actionId === 'export_jira' ||
      actionId === 'export_markdown'
    ) {
      openExportConfirm()
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

  async function handleBatchAction(actionId) {
    if (actionId === 'extract_features' && (features?.length ?? 0) > 0) {
      setRegenConfirm({
        title: 'Regenerate features?',
        message: regenerateConfirmMessage('features'),
        actionId,
      })
      return
    }
    await executeBatchAction(actionId)
  }

  async function handlePrimaryAction(stageId) {
    setActiveStage(stageId)

    if (stageId === 'features') {
      const featurePending = pipeline?.stages.features.pending ?? 0
      if (featurePending > 0) {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'feature') ?? reviewQueue[0]
        if (first) selectItem(first)
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
        if (first) selectItem(first)
      }
      return
    }

    if (stageId === 'stories') {
      if (pipeline?.stages.stories.counts?.total === 0) {
        await handleBatchAction('batch_stories')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'story')
        if (first) selectItem(first)
      }
      return
    }

    if (stageId === 'tests') {
      if (pipeline?.stages.tests.counts?.total === 0) {
        await handleBatchAction('batch_tests')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'test_case')
        if (first) selectItem(first)
      }
      return
    }

    if (stageId === 'points') {
      if (pipeline?.stages.points.status === 'not_started') {
        await handleBatchAction('batch_points')
      } else {
        setWorkspaceTab('queue')
        const first = reviewQueue.find((i) => i.type === 'points')
        if (first) selectItem(first)
      }
      return
    }

    if (stageId === 'export') {
      openExportConfirm()
    }
  }

  function handleSuggestedAction(step) {
    if (step.action === 'review') {
      setWorkspaceTab('queue')
      if (reviewQueue[0]) selectItem(reviewQueue[0])
      return
    }
    if (
      step.action === 'export_csv' ||
      step.action === 'export_jira' ||
      step.action === 'export_markdown'
    ) {
      openExportConfirm()
      return
    }
    if (step.action) {
      handleBatchAction(step.action)
    }
  }

  function handleOpenChunk(chunkId, sourceExcerpt) {
    setProvenance({ chunkId, sourceExcerpt: sourceExcerpt ?? null })
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
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => setShowSettings((v) => !v)}
          >
            {showSettings ? 'Hide preferences' : 'Generation preferences'}
          </button>
        </div>
      </div>

      {showSettings && (
        <section className="panel">
          <h2>Generation preferences</h2>
          <p className="empty-hint">
            Changes apply the next time you extract or generate — they do not rewrite approved items.
          </p>
          <form onSubmit={handleSaveSettings}>
            <PipelineSettingsForm settings={settings} onChange={setSettings} />
            <div className="upload-form-actions" style={{ marginTop: '1rem' }}>
              <button type="submit" className="btn btn-primary" disabled={savingSettings}>
                {savingSettings ? 'Saving…' : 'Save preferences'}
              </button>
            </div>
            {settingsStatus && (
              <p className={settingsStatus.includes('saved') ? 'form-success' : 'form-error'}>
                {settingsStatus}
              </p>
            )}
          </form>
        </section>
      )}

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

      {regenConfirm && (
        <ConfirmModal
          title={regenConfirm.title}
          message={regenConfirm.message}
          confirmLabel="Regenerate"
          onConfirm={() => executeBatchAction(regenConfirm.actionId)}
          onClose={() => setRegenConfirm(null)}
        />
      )}

      {exportConfirm && (
        <ExportReadyModal
          exportReadiness={exportReadiness}
          busy={busy}
          onExport={(format) => {
            void handleExport(format)
          }}
          onClose={() => setExportConfirm(false)}
        />
      )}

      {provenance && (
        <ChunkProvenanceModal
          brdId={brdId}
          chunkId={provenance.chunkId}
          sourceExcerpt={provenance.sourceExcerpt}
          onClose={() => setProvenance(null)}
        />
      )}

      <PipelineStepper
        stages={pipeline?.stages}
        activeStage={activeStage}
        onStageClick={handleStageClick}
        onPrimaryAction={handlePrimaryAction}
        busy={busy || loading}
        exportReadiness={exportReadiness}
      />

      {brdReady && pipeline?.stages?.export?.status === 'ready' && (
        <div className="export-ready-banner" role="status">
          <div>
            <strong>Ready to export</strong>
            <span className="meta"> — {exportReadinessLabel(exportReadiness)}</span>
          </div>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy || loading}
            onClick={openExportConfirm}
          >
            Export…
          </button>
        </div>
      )}

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

          <div
            className={`workspace-split ${detailInMiddle ? 'workspace-split-detail-first' : ''} ${
              isNarrow && selectedItem ? 'workspace-split-mobile-detail' : ''
            }`}
          >
            {treeOpen && (
              <>
                {isNarrow && (
                  <button
                    type="button"
                    className="workspace-sheet-backdrop"
                    aria-label="Close structure"
                    onClick={() => setTreeOpen(false)}
                  />
                )}
                <TreeSidebar
                  features={features ?? []}
                  subFeatures={subFeatures ?? []}
                  stories={stories ?? []}
                  testCases={testCases ?? []}
                  selectedItem={selectedItem}
                  onSelect={selectItem}
                  onClose={() => setTreeOpen(false)}
                />
              </>
            )}

            <div
              className={`workspace-main ${detailInMiddle && !isNarrow ? 'workspace-main-compact' : ''} ${
                !selectedItem && !isNarrow ? 'workspace-main-solo' : ''
              }`}
            >
              {workspaceTab === 'overview' && (
                <OverviewTab
                  brdId={brd.id}
                  pipeline={pipeline}
                  reviewQueue={reviewQueue}
                  blockers={blockers}
                  suggestedStep={suggestedStep}
                  recentJobs={recentJobs}
                  batchActions={batchActions}
                  exportReadiness={exportReadiness}
                  busy={busy || loading}
                  onGoToQueue={() => {
                    setWorkspaceTab('queue')
                    if (reviewQueue[0]) selectItem(reviewQueue[0])
                  }}
                  onSuggestedAction={handleSuggestedAction}
                  onBatchAction={handleBatchAction}
                />
              )}

              {workspaceTab === 'queue' && (
                <ReviewQueue
                  items={reviewQueue}
                  selectedItem={selectedItem}
                  onSelect={selectItem}
                  filter={queueFilter}
                  onFilterChange={setQueueFilter}
                  parentFilter={parentFilter}
                  onParentFilterChange={setParentFilter}
                  busy={busy || loading}
                  onBulkApprove={handleBulkApprove}
                  bulkStatus={bulkStatus}
                  suggestedStep={suggestedStep}
                  onSuggestedAction={handleSuggestedAction}
                />
              )}
            </div>

            {selectedItem && (
              <>
                {isNarrow && (
                  <button
                    type="button"
                    className="workspace-sheet-backdrop"
                    aria-label="Close detail"
                    onClick={() => setSelectedItem(null)}
                  />
                )}
                <DetailPanel
                  item={selectedItem}
                  busy={busy}
                  onClose={() => setSelectedItem(null)}
                  onRefresh={refreshAll}
                  onSelectItem={selectItem}
                  onRunJob={handleRunJob}
                  onApprove={() => handleApproveItem(selectedItem)}
                  onReject={() => handleRejectItem(selectedItem)}
                  onOpenChunk={handleOpenChunk}
                  editRequestKey={editRequestKey}
                  onEditRequestHandled={() => setEditRequestKey(null)}
                  parents={parents}
                  wide={detailInMiddle && !isNarrow}
                />
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}
