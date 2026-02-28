import React, { useCallback, useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import ScoutNet from '../components/ScoutNet'
import type { SiteData } from '../siteDetection'
import { EMPTY_SITE_DATA } from '../siteDetection'
import { getPreviewImage, PREVIEW_API_URL } from '../previewApi'
import { callPersuade, type PersuasionResponse } from '../secondStageApi'
import '../styles/ScoutNet.css'

const SESSION_KEY_DETECTION = 'scoutnet_last_detection'
const SESSION_KEY_PENDING = 'scoutnet_pending_navigation'

type PendingNavigation = {
  tabId: number
  targetUrl: string
  sourceUrl?: string
  siteData: SiteData | null
  createdAt: number
}

type ProceedStep = 'idle' | 'reason' | 'preview'

function WarningApp() {
  const [siteData, setSiteData] = useState<SiteData | null>(null)
  const [pending, setPending] = useState<PendingNavigation | null>(null)
  const [loading, setLoading] = useState(true)
  const [proceedStep, setProceedStep] = useState<ProceedStep>('idle')
  const [reasonToVisit, setReasonToVisit] = useState('')
  const [previewImage, setPreviewImage] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState(false)
  const [previewUrlInvalid, setPreviewUrlInvalid] = useState(false)
  const [persuadeResult, setPersuadeResult] = useState<PersuasionResponse | null>(null)
  const [persuadeLoading, setPersuadeLoading] = useState(false)
  const [persuadeError, setPersuadeError] = useState(false)

  const readSession = useCallback(() => {
    return chrome.storage.session.get([SESSION_KEY_DETECTION, SESSION_KEY_PENDING]).then((result) => {
      const p = result[SESSION_KEY_PENDING] as PendingNavigation | undefined
      setPending(p ?? null)
      const data = p?.siteData ?? (result[SESSION_KEY_DETECTION] as SiteData | undefined)
      setSiteData(data ?? null)
    })
  }, [])

  useEffect(() => {
    readSession().then(() => setLoading(false))
  }, [readSession])

  useEffect(() => {
    const listener = (
      changes: { [key: string]: chrome.storage.StorageChange },
      areaName: string
    ) => {
      if (areaName !== 'session') return
      if (SESSION_KEY_DETECTION in changes || SESSION_KEY_PENDING in changes) readSession()
    }
    chrome.storage.onChanged.addListener(listener)
    return () => chrome.storage.onChanged.removeListener(listener)
  }, [readSession])

  const onLeaveSite = useCallback(() => {
    chrome.runtime.sendMessage({ type: 'LEAVE_SITE' })
  }, [])

  /** When user clicks "Confirm 前往" in ScoutNet (after reason + persuade in ScoutNet): navigate to target URL */
  const onProceedToUrl = useCallback(() => {
    if (!pending?.targetUrl) return
    chrome.runtime.sendMessage({ type: 'PROCEED_TO_URL' })
  }, [pending?.targetUrl])

  /** Submit: 打包 user_input + first_stage_report → call persuade API → 下一畫面先 loading 再顯示回傳內容 */
  const onSubmitReason = useCallback(async () => {
    console.log('[ScoutNet] onSubmitReason called', {
      hasPending: !!pending,
      targetUrl: pending?.targetUrl,
      reasonLength: reasonToVisit.trim().length,
      hasReport: !!(pending?.siteData?.report),
    })
    if (!pending?.targetUrl || !reasonToVisit.trim()) {
      console.warn('[ScoutNet] onSubmitReason early return: missing targetUrl or reason')
      return
    }
    const url = pending.targetUrl
    const isHttp = url.startsWith('http://') || url.startsWith('https://')
    const isExtension = url.startsWith('chrome-extension://') || url.startsWith('moz-extension://')

    setProceedStep('preview')
    setPersuadeResult(null)
    setPersuadeError(false)
    setPersuadeLoading(true)
    setPreviewLoading(true)
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(!isHttp || isExtension)

    const user_input = reasonToVisit.trim()
    const firstStageReport = pending?.siteData?.report
      ? (JSON.parse(JSON.stringify(pending.siteData.report)) as Record<string, unknown>)
      : {}
    console.log('[ScoutNet] calling persuade API with user_input and first_stage_report keys:', Object.keys(firstStageReport))
    let result: PersuasionResponse | null = null
    try {
      result = await callPersuade(user_input, firstStageReport)
      console.log('[ScoutNet] persuade API returned', result ? 'OK' : 'null')
    } catch (err) {
      console.error('[ScoutNet] persuade API threw', err)
    }
    setPersuadeLoading(false)
    if (result) setPersuadeResult(result)
    else setPersuadeError(true)

    if (!isHttp || isExtension) {
      setPreviewLoading(false)
      return
    }
    const dataUrl = await getPreviewImage(url)
    setPreviewLoading(false)
    if (dataUrl) setPreviewImage(dataUrl)
    else setPreviewError(true)
  }, [pending?.targetUrl, pending?.siteData?.report, reasonToVisit])

  const onCancelReason = useCallback(() => {
    setProceedStep('idle')
    setReasonToVisit('')
    setPersuadeResult(null)
    setPersuadeLoading(false)
    setPersuadeError(false)
  }, [])

  const onConfirmProceed = useCallback(async () => {
    setProceedStep('idle')
    setReasonToVisit('')
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(false)
    setPersuadeResult(null)
    setPersuadeLoading(false)
    setPersuadeError(false)
    await chrome.runtime.sendMessage({ type: 'PROCEED_TO_URL' })
  }, [])

  /** Back = user chose to leave the website (same as "Leave site") */
  const onClosePreview = useCallback(() => {
    setProceedStep('idle')
    setReasonToVisit('')
    setPreviewImage(null)
    setPreviewError(false)
    setPreviewUrlInvalid(false)
    setPersuadeResult(null)
    setPersuadeLoading(false)
    setPersuadeError(false)
    onLeaveSite()
  }, [onLeaveSite])

  if (loading) {
    return (
      <div className="scoutnet-container" style={{ justifyContent: 'center' }}>
        <p style={{ fontFamily: 'inherit', fontSize: '1rem' }}>Loading…</p>
      </div>
    )
  }

  const detecting = Boolean(pending && siteData === null)

  if (detecting) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(0, 0, 0, 0.35)',
          backdropFilter: 'blur(4px)',
        }}
      >
        <div
          style={{
            background: '#fff',
            borderRadius: 12,
            boxShadow: '0 4px 20px rgba(0,0,0,0.15), 0 0 1px rgba(0,0,0,0.1)',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            minWidth: 200,
            maxWidth: 320,
          }}
        >
          <div
            style={{
              width: 16,
              height: 16,
              flexShrink: 0,
              borderRadius: '999px',
              border: '2px solid rgba(0,0,0,0.1)',
              borderTopColor: '#f59e0b',
              animation: 'scoutnet-spin 0.7s linear infinite',
            }}
          />
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#334155' }}>Detecting…</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Checking this link. Please wait.</div>
          </div>
        </div>
      </div>
    )
  }

  const data = siteData ?? pending?.siteData ?? EMPTY_SITE_DATA

  return (
    <>
      <ScoutNet
        siteData={siteData ?? undefined}
        onLeaveSite={onLeaveSite}
        onProceedToUrl={onProceedToUrl}
      />
      {/* Step 1: Why do you want to still go to the website? — submit here triggers POST /api/v1/scan/persuade */}
      {proceedStep === 'reason' && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 16,
              maxWidth: 480,
              width: '100%',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              padding: 24,
            }}
          >
            <h3 style={{ margin: '0 0 8px', fontSize: 18 }}>Why do you want to still go to the website?</h3>
            <p style={{ margin: '0 0 16px', fontSize: 14, color: '#64748b' }}>
              Please fill in your reason (required). We’ll then call the persuade API and show ScoutNet’s suggestions; you can then confirm to visit.
            </p>
            <textarea
              value={reasonToVisit}
              onChange={(e) => setReasonToVisit(e.target.value)}
              placeholder="e.g. I need to check something for school"
              rows={3}
              required
              style={{
                width: '100%',
                padding: 12,
                borderRadius: 8,
                border: reasonToVisit.trim() ? '1px solid #e2e8f0' : '1px solid #f59e0b',
                fontSize: 14,
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
            {reasonToVisit.trim().length === 0 && (
              <p style={{ margin: '4px 0 0', fontSize: 12, color: '#b45309' }}>此欄位必填，請填寫原因後再提交。</p>
            )}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 16 }}>
              <button
                type="button"
                onClick={onCancelReason}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontSize: 14,
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={onSubmitReason}
                disabled={!reasonToVisit.trim()}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: reasonToVisit.trim() ? '#f59e0b' : '#cbd5e1',
                  color: '#fff',
                  cursor: reasonToVisit.trim() ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Step 2: Preview + dangers + confirm */}
      {proceedStep === 'preview' && (
        <div
          className="scoutnet-preview-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxSizing: 'border-box',
          }}
        >
          <div
            className="scoutnet-preview-modal"
            style={{
              background: '#fff',
              borderRadius: 16,
              maxWidth: 720,
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
              padding: 24,
            }}
          >
            <h3 style={{ margin: '0 0 16px', fontSize: 18 }}>請確認後再前往</h3>
            {pending?.targetUrl && (
              <p style={{ margin: '0 0 12px', fontSize: 12, color: '#64748b', wordBreak: 'break-all' }}>
                URL: {pending.targetUrl}
              </p>
            )}
            {/* Submit 後先 loading，persuade API 回傳後再顯示底下內容 */}
            {persuadeLoading && (
              <div style={{ marginBottom: 24, padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, background: '#f8fafc', borderRadius: 12 }}>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    border: '2px solid #e2e8f0',
                    borderTopColor: '#f59e0b',
                    borderRadius: '50%',
                    animation: 'scoutnet-spin 0.7s linear infinite',
                  }}
                />
                <span style={{ fontSize: 14, color: '#64748b' }}>正在取得 ScoutNet 的建議…</span>
              </div>
            )}
            {!persuadeLoading && (
              <>
            {/* 您的原因 — 等同 API 回傳的 user_input */}
            {reasonToVisit.trim() && (
              <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8, borderLeft: '4px solid #94a3b8' }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: 600, color: '#475569' }}>您的原因</p>
                <p style={{ margin: '6px 0 0', fontSize: 14, color: '#334155', lineHeight: 1.5 }}>{reasonToVisit.trim()}</p>
              </div>
            )}
            {/* first_stage_report_summary：API 回傳的風險摘要 */}
            {persuadeResult?.first_stage_report_summary && (
              <div style={{ marginBottom: 16, padding: 12, background: '#fef2f2', borderRadius: 8, border: '1px solid #fecaca' }}>
                <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: '#991b1b' }}>風險摘要</p>
                {persuadeResult.first_stage_report_summary.target_url && (
                  <p style={{ margin: 0, fontSize: 12, color: '#b91c1c', wordBreak: 'break-all' }}>
                    網址：{String(persuadeResult.first_stage_report_summary.target_url)}
                  </p>
                )}
                <p style={{ margin: '6px 0 0', fontSize: 13, color: '#991b1b' }}>
                  {[
                    persuadeResult.first_stage_report_summary.risk_label != null && String(persuadeResult.first_stage_report_summary.risk_label),
                    persuadeResult.first_stage_report_summary.risk_level != null && `風險等級：${String(persuadeResult.first_stage_report_summary.risk_level)}`,
                    persuadeResult.first_stage_report_summary.risk_score != null && `安全分數：${Number(persuadeResult.first_stage_report_summary.risk_score)}`,
                    persuadeResult.first_stage_report_summary.risk_source != null && `來源：${String(persuadeResult.first_stage_report_summary.risk_source)}`,
                  ].filter(Boolean).join(' · ')}
                </p>
              </div>
            )}
            {persuadeError && (
              <p style={{ margin: '0 0 16px', padding: 12, background: '#fef2f2', borderRadius: 8, fontSize: 14, color: '#991b1b' }}>
                無法取得建議，您仍可確認前往或返回。
              </p>
            )}
            {/* second_stage_result：API 回傳的建議與想法 */}
            {persuadeResult?.second_stage_result && (
              <div style={{ marginBottom: 16, padding: 16, background: '#f0f9ff', borderRadius: 12, border: '1px solid #bae6fd', borderLeft: '4px solid #0284c7' }}>
                <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: '#0369a1' }}>ScoutNet 提出的建議與想法</p>
                {/* reason_analysis: empathy_note / analysis */}
                {(persuadeResult.second_stage_result.reason_analysis?.empathy_note ||
                  persuadeResult.second_stage_result.reason_analysis?.analysis) && (
                  <p style={{ margin: 0, fontSize: 14, color: '#0c4a6e', lineHeight: 1.5 }}>
                    {persuadeResult.second_stage_result.reason_analysis.empathy_note ||
                      persuadeResult.second_stage_result.reason_analysis.analysis}
                  </p>
                )}
                {/* behavior_consequence_warning */}
                {persuadeResult.second_stage_result.behavior_consequence_warning && (
                  <p style={{ margin: '10px 0 0', fontSize: 13, color: '#075985', lineHeight: 1.5 }}>
                    {persuadeResult.second_stage_result.behavior_consequence_warning}
                  </p>
                )}
                {/* general_warnings */}
                {(persuadeResult.second_stage_result.general_warnings?.length ?? 0) > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <p style={{ margin: '0 0 4px', fontSize: 12, fontWeight: 600, color: '#0369a1' }}>一般提醒</p>
                    <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#0c4a6e' }}>
                      {persuadeResult.second_stage_result.general_warnings!.map((w: string, i: number) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* recommended_actions */}
                {(persuadeResult.second_stage_result.recommended_actions?.length ?? 0) > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <p style={{ margin: '0 0 6px', fontSize: 12, fontWeight: 600, color: '#0369a1' }}>建議做法</p>
                    <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#0c4a6e' }}>
                      {persuadeResult.second_stage_result.recommended_actions!.map((a: string, i: number) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* encouraging_message */}
                {persuadeResult.second_stage_result.encouraging_message && (
                  <p style={{ margin: '12px 0 0', fontSize: 14, fontWeight: 500, color: '#0369a1' }}>
                    {persuadeResult.second_stage_result.encouraging_message}
                  </p>
                )}
              </div>
            )}
            {/* Dangers of this site */}
            <div style={{ marginBottom: 16, padding: 12, background: '#fef2f2', borderRadius: 8, border: '1px solid #fecaca' }}>
              <p style={{ margin: '0 0 8px', fontSize: 14, fontWeight: 600, color: '#991b1b' }}>⚠️ Risks of this site</p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: data.warnings.length > 0 ? 8 : 0 }}>
                <span style={{ fontSize: 13, color: '#b91c1c' }}>
                  Safety: {data.riskScore} · {data.riskLevel === 'high' ? 'High risk' : data.riskLevel === 'medium' ? 'Medium risk' : 'Low risk'}
                </span>
              </div>
              {data.warnings.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: '#991b1b' }}>
                  {data.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              )}
              {data.correctUrl && (
                <p style={{ margin: '8px 0 0', fontSize: 12, color: '#b91c1c' }}>
                  The real site you may want is: {data.correctUrl}
                </p>
              )}
            </div>
            {previewUrlInvalid && !previewLoading && (
              <p style={{ margin: 0, padding: '12px', background: '#fef2f2', borderRadius: 8, fontSize: 14, color: '#991b1b' }}>
                This URL cannot be previewed (only http/https supported). You can still click "Confirm" to visit.
              </p>
            )}
            {!previewUrlInvalid && previewLoading && (
              <p style={{ margin: 0, color: '#64748b' }}>Loading preview…</p>
            )}
            {!previewUrlInvalid && previewError && !previewLoading && (
              <p style={{ margin: 0, padding: '12px', background: '#f8fafc', borderRadius: 8, fontSize: 14, color: '#475569' }}>
                Preview is optional. If the backend is not running, you can skip and click "Confirm" to visit.
                <br />
                <span style={{ fontSize: 12, color: '#94a3b8', wordBreak: 'break-all' }}>Backend: {PREVIEW_API_URL}</span>
              </p>
            )}
            {!previewUrlInvalid && previewImage && !previewLoading && (
              <img
                src={previewImage}
                alt="Site preview"
                style={{ width: '100%', height: 'auto', borderRadius: 8, display: 'block', marginBottom: 16 }}
              />
            )}
            <p style={{ margin: '0 0 16px', fontSize: 14, color: '#64748b' }}>
              Are you sure you want to visit this site?
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={onClosePreview}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: '1px solid #cbd5e1',
                  background: '#fff',
                  cursor: 'pointer',
                  fontSize: 14,
                }}
              >
                Back
              </button>
              <button
                type="button"
                onClick={onConfirmProceed}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: '#f59e0b',
                  color: '#fff',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: 14,
                }}
              >
                Confirm
              </button>
            </div>
              </>
            )}
          </div>
        </div>
      )}
    </>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <WarningApp />
  </React.StrictMode>,
)
