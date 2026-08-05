import { useMemo, useState } from 'react'
import { useJobs } from '../context/JobsContext'
import { useBrdPipeline } from '../hooks/useBrdPipeline'
import { runBatchAction } from '../utils/batchActions'
import { getBatchActions, getBlockers, getSuggestedStep } from '../utils/pipeline'
import { DetailPanel } from './DetailPanel'
import { FeatureTile } from './FeatureTile'
import { OverviewTab } from './OverviewTab'
import { PipelineStepper } from './PipelineStepper'
import { ReviewQueue } from './ReviewQueue'
import { StatusBadge } from './StatusBadge'

export function BrdWorkspace({ brd, onRefreshBrd }) {
  const brdId = brd.id
  const { trackJob, jobs } = useJobs()
  const { features, subFeatures, stories, pipeline, reviewQueue, loading, error: pipelineError, reload } = useBrdPipeline(brdId, brd.status)
  const [selectedItem, setSelectedItem] = useState(null)
  const [queueFilter, setQueueFilter] = useState('all')
  const [parentFilter, setParentFilter] = useState('all')
  const [activeStage, setActiveStage] = useState('features')
  const [busy, setBusy] = useState(false)
  const [showContent, setShowContent] = useState(false)
  const [workspaceTab, setWorkspaceTab] = useState('overview')

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

  async function handleBatchAction(actionId) {
    setBusy(true)
    try {
      await runBatchAction(actionId, {
        brdId,
        features: features ?? [],
        subFeatures: subFeatures ?? [],
        stories: stories ?? [],
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
    }
  }

  function handleSuggestedAction(step) {
    if (step.action === 'review') {
      setWorkspaceTab('queue')
      if (reviewQueue[0]) setSelectedItem(reviewQueue[0])
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
          {loading && (
            <p className="empty-hint workspace-loading">Loading pipeline data…</p>
          )}
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
            <button
              type="button"
              className={`workspace-tab ${workspaceTab === 'browse' ? 'workspace-tab-active' : ''}`}
              onClick={() => setWorkspaceTab('browse')}
            >
              Browse
            </button>
          </div>

          <div className={`workspace-split ${workspaceTab === 'overview' ? 'workspace-split-full' : ''}`}>
            <div className="workspace-main">
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
                  selectedId={selectedItem?.id}
                  onSelect={setSelectedItem}
                  filter={queueFilter}
                  onFilterChange={setQueueFilter}
                  parentFilter={parentFilter}
                  onParentFilterChange={setParentFilter}
                />
              )}

              {workspaceTab === 'browse' && (
                <section className="browse-panel">
                  <div className="section-toolbar">
                    <h2>Features</h2>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => handleBatchAction('extract_features')}
                      disabled={busy || loading}
                    >
                      {features?.length > 0 ? 'Regenerate features' : 'Extract features'}
                    </button>
                  </div>
                  {features?.length === 0 && <p className="empty-hint">No features yet.</p>}
                  {features?.length > 0 && (
                    <div className="feature-grid">
                      {features.map((f) => (
                        <FeatureTile
                          key={f.id}
                          feature={f}
                          onClick={() =>
                            setSelectedItem({
                              id: f.id,
                              type: 'feature',
                              title: f.title,
                              parentLabel: '—',
                              confidence: f.confidence,
                              status: f.status,
                              entity: f,
                            })
                          }
                        />
                      ))}
                    </div>
                  )}
                </section>
              )}
            </div>

            {workspaceTab !== 'overview' && (
              <DetailPanel
                item={selectedItem}
                busy={busy}
                onClose={() => setSelectedItem(null)}
                onRefresh={refreshAll}
                onSelectItem={setSelectedItem}
                onRunJob={handleRunJob}
              />
            )}
          </div>
        </>
      )}

      {(brd.preview || brd.parsed_text) && (
        <details className="panel parsed-collapsible">
          <summary>Parsed BRD content</summary>
          {brd.preview && !showContent && (
            <>
              <pre className="content-preview">{brd.preview}</pre>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowContent(true)}>
                Load full parsed content
              </button>
            </>
          )}
          {showContent && brd.parsed_text && <pre className="content-preview">{brd.parsed_text}</pre>}
        </details>
      )}
    </div>
  )
}
