import React, { useState, useRef, useEffect, useCallback } from 'react';
import '../styles/ScoutNet.css';
import { EMPTY_SITE_DATA, type SiteData, type ReportData } from '../siteDetection';
import { callPersuade, type PersuasionResponse } from '../secondStageApi';

type Step =
  | 'rating'
  | 'question'
  | 'quiz_result'
  | 'learning'
  | 'tips'
  | 'next_steps'
  | 'confirm'
  | 'enter'
  | 'persuade_result';

type ConversationEntry = { step: Step; userReply: string };

export type ScoutNetProps = {
  /** Site data from detection/extension; if not provided, empty data is used */
  siteData?: SiteData | null;
  /** Called when user clicks "Leave site" on the warning page */
  onLeaveSite?: () => void;
  /** Called when user chooses to proceed to the risky URL */
  onProceedToUrl?: () => void;
};

const ScoutNet: React.FC<ScoutNetProps> = ({ siteData: siteDataProp, onLeaveSite, onProceedToUrl }) => {
  const [currentStep, setCurrentStep] = useState<Step>('rating');
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [selectedQuizExplanation, setSelectedQuizExplanation] = useState<string | null>(null);
  const [enterReason, setEnterReason] = useState('');
  const [persuadeResult, setPersuadeResult] = useState<PersuasionResponse | null>(null);
  const [persuadeLoading, setPersuadeLoading] = useState(false);
  const [persuadeError, setPersuadeError] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

  const siteData: SiteData = siteDataProp ?? EMPTY_SITE_DATA;
  const report: ReportData | null | undefined = siteData.report;

  const scrollToTop = () => {
    threadRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const scrollToBottom = () => {
    const el = threadRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  };

  useEffect(() => {
    if (conversation.length === 0) {
      scrollToTop();
    } else {
      scrollToBottom();
    }
  }, [conversation, currentStep]);

  const resetFlow = () => {
    setCurrentStep('rating');
    setConversation([]);
    setSelectedQuizExplanation(null);
    setEnterReason('');
    setPersuadeResult(null);
    setPersuadeLoading(false);
    setPersuadeError(false);
  };

  /** Submit in ScoutNet: 打包 user_input + first_stage_report → call persuade API → 顯示結果 */
  const onSubmitReason = useCallback(async () => {
    if (!enterReason.trim()) return;
    setConversation((prev) => [...prev, { step: 'enter', userReply: enterReason.trim() }]);
    const firstStageReport = report
      ? (JSON.parse(JSON.stringify(report)) as Record<string, unknown>)
      : {};
    setPersuadeLoading(true);
    setPersuadeResult(null);
    setPersuadeError(false);
    const result = await callPersuade(enterReason.trim(), firstStageReport);
    setPersuadeLoading(false);
    if (result) setPersuadeResult(result);
    else setPersuadeError(true);
    setCurrentStep('persuade_result');
  }, [enterReason, report]);

  const sendReply = (userReply: string, nextStep: Step) => {
    setConversation((prev) => [...prev, { step: currentStep, userReply }]);
    setCurrentStep(nextStep);
  };

  // Fox message bubbles only (no reply UI) — left side: our website guardian
  const renderFoxBubbles = (step: Step) => (
    <div className="chat-message chat-message--fox">
      <div className="chat-fox-side">
        <div className="chat-avatar" aria-hidden>🦊</div>
      </div>
      <div className="chat-bubbles">
        {step === 'rating' && (
          <>
            <div className="chat-bubble">
              <p className="chat-bubble-text">
                {report?.kid_friendly_summary?.simple_message ??
                  report?.kid_friendly_summary?.title ??
                  (report ? 'I checked this link — it looks risky. Here\'s what I found.' : 'Waiting for result…')}
              </p>
            </div>
            <div className="chat-bubble chat-bubble--card">
              <div className="risk-badge risk-badge--inline">
                <span className="risk-icon">{report?.report_metadata?.risk?.icon ?? '⚠️'}</span>
                <span className="risk-level">
                  {report?.report_metadata?.risk?.label ??
                    (siteData.riskLevel === 'high' ? 'High-risk site' : siteData.riskLevel === 'medium' ? 'Medium-risk site' : 'Risk check')}
                </span>
                <span className="risk-score">Safety {siteData.riskScore}</span>
              </div>
              <div className="url-comparison url-comparison--compact">
                <div className="url-item">
                  <span className="url-label">You're visiting</span>
                  <span className="url-current">{siteData.currentUrl}</span>
                </div>
                {siteData.correctUrl && (
                  <div className="url-item">
                    <span className="url-label">Correct URL</span>
                    <span className="url-correct">{siteData.correctUrl}</span>
                  </div>
                )}
              </div>
              {report?.kid_friendly_summary?.short_explanation && (
                <p className="chat-bubble-text" style={{ marginBottom: 8 }}>
                  {report.kid_friendly_summary.short_explanation}
                </p>
              )}
              {(report?.evidence_cards?.length ?? 0) > 0 ? (
                <>
                  <p className="chat-bubble-label">Evidence</p>
                  {report!.evidence_cards!.map((card, index) => (
                    <div key={card.id ?? index} className="warning-item warning-item--compact">
                      <span className="warning-dot">{card.icon ?? index + 1}</span>
                      <span className="warning-text">{card.title ?? card.content}</span>
                    </div>
                  ))}
                </>
              ) : siteData.warnings.length > 0 ? (
                <>
                  <p className="chat-bubble-label">Suspicious things we spotted:</p>
                  {siteData.warnings.map((warning, index) => (
                    <div key={index} className="warning-item warning-item--compact">
                      <span className="warning-dot">{index + 1}</span>
                      <span className="warning-text">{warning}</span>
                    </div>
                  ))}
                </>
              ) : null}
            </div>
          </>
        )}
        {step === 'question' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">Answer the question in the popup below.</p>
          </div>
        )}
        {step === 'quiz_result' && selectedQuizExplanation && (
          <div className="chat-bubble chat-bubble--card">
            <p className="chat-bubble-text">{selectedQuizExplanation}</p>
          </div>
        )}
        {step === 'learning' && (
          <div className="chat-bubble chat-bubble--success">
            {report?.interactive_quiz?.learning_point && (
              <p className="chat-bubble-text" style={{ marginBottom: 8 }}>{report.interactive_quiz.learning_point}</p>
            )}
            {report?.interactive_quiz?.correct_answer_id && (() => {
              const opt = report.interactive_quiz?.options?.find(
                (o) => o.id === report.interactive_quiz?.correct_answer_id
              );
              return (
                <p className="chat-bubble-text" style={{ marginBottom: 4 }}>
                  Correct answer: {opt?.text ?? report.interactive_quiz.correct_answer_id}
                </p>
              );
            })()}
            {report?.interactive_quiz?.difficulty && (
              <p className="chat-bubble-note">Difficulty: {report.interactive_quiz.difficulty}</p>
            )}
          </div>
        )}
        {step === 'tips' && (
          <div className="chat-bubble chat-bubble--tips">
            <p className="chat-bubble-label">🔒 Safety tips</p>
            <ul className="chat-bubble-list">
              {(report?.safety_tips?.length ?? 0) > 0
                ? report!.safety_tips!.map((t) => (
                    <li key={t.id ?? t.tip}>
                      {t.icon && <span className="tip-icon">{t.icon} </span>}
                      {t.tip}
                    </li>
                  ))
                : null}
            </ul>
          </div>
        )}
        {step === 'next_steps' && (
          <div className="chat-bubble chat-bubble--tips">
            <p className="chat-bubble-label">Recommended actions</p>
            <ul className="chat-bubble-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
              {(report?.next_steps?.length ?? 0) > 0
                ? report!.next_steps!.map((s, i) => (
                    <li
                      key={i}
                      style={{
                        marginBottom: 8,
                        paddingLeft: 12,
                        borderLeftWidth: 3,
                        borderLeftStyle: 'solid',
                        borderLeftColor: s.priority === 'high' ? '#dc2626' : '#ca8a04',
                      }}
                    >
                      {s.icon && <span className="tip-icon">{s.icon} </span>}
                      {s.priority && (
                        <span style={{ fontSize: 12, color: '#64748b', marginRight: 6 }}>
                          {s.priority === 'high' ? 'High' : 'Medium'}
                        </span>
                      )}
                      {s.link ? (
                        <a href={s.link} target="_blank" rel="noopener noreferrer" className="chat-link">
                          {s.action}
                        </a>
                      ) : (
                        s.action
                      )}
                    </li>
                  ))
                : null}
            </ul>
          </div>
        )}
        {step === 'confirm' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">Do you want to enter this site?</p>
          </div>
        )}
        {step === 'enter' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">Why do you want to still go to the website? Please fill in your reason (required), then click Submit. We’ll call the persuade API and show ScoutNet’s suggestions.</p>
          </div>
        )}
        {step === 'persuade_result' && (
          <div className="chat-bubble chat-bubble--card">
            {persuadeLoading && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="scoutnet-typing-indicator">
                  ScoutNet 正在輸入中 typing
                  <span className="dot" />
                  <span className="dot" />
                  <span className="dot" />
                </span>
              </div>
            )}
            {persuadeError && !persuadeLoading && <p className="chat-bubble-text" style={{ color: '#991b1b' }}>無法取得建議，您仍可確認前往或返回。</p>}
            {persuadeResult && !persuadeLoading && (
              <>
                <p className="chat-bubble-label">您的原因</p>
                <p className="chat-bubble-text" style={{ marginBottom: 8 }}>{enterReason.trim()}</p>
                {persuadeResult.first_stage_report_summary && (
                  <p className="chat-bubble-note" style={{ marginBottom: 8 }}>
                    {[persuadeResult.first_stage_report_summary.risk_label, persuadeResult.first_stage_report_summary.risk_level, persuadeResult.first_stage_report_summary.risk_score != null && `安全分數 ${persuadeResult.first_stage_report_summary.risk_score}`].filter(Boolean).join(' · ')}
                  </p>
                )}
                {persuadeResult.second_stage_result?.reason_analysis?.empathy_note && (
                  <p className="chat-bubble-text" style={{ marginBottom: 6 }}>{persuadeResult.second_stage_result.reason_analysis.empathy_note}</p>
                )}
                {persuadeResult.second_stage_result?.behavior_consequence_warning && (
                  <p className="chat-bubble-text" style={{ marginBottom: 6, fontSize: 13 }}>{persuadeResult.second_stage_result.behavior_consequence_warning}</p>
                )}
                {(persuadeResult.second_stage_result?.general_warnings?.length ?? 0) > 0 && (
                  <ul style={{ margin: '4px 0 8px', paddingLeft: 20, fontSize: 13 }}>
                    {persuadeResult.second_stage_result.general_warnings!.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                )}
                {(persuadeResult.second_stage_result?.recommended_actions?.length ?? 0) > 0 && (
                  <ul style={{ margin: '4px 0 8px', paddingLeft: 20, fontSize: 13 }}>
                    {persuadeResult.second_stage_result.recommended_actions!.map((a: string, i: number) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                )}
                {persuadeResult.second_stage_result?.encouraging_message && (
                  <p className="chat-bubble-text" style={{ marginTop: 8, fontWeight: 500 }}>{persuadeResult.second_stage_result.encouraging_message}</p>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );

  // User message — right side: reserved and shown for every reply
  const renderUserBubble = (text: string) => (
    <div className="chat-message chat-message--user">
      <div className="chat-user-side">
        <div className="chat-bubble chat-bubble--user">
          <p className="chat-bubble-text">{text}</p>
        </div>
        <div className="chat-avatar chat-avatar--user" aria-hidden>🐰</div>
      </div>
    </div>
  );

  // Reply UI for current step only
  const renderReplyInput = () => {
    if (currentStep === 'rating') {
      const hasQuiz = report?.interactive_quiz?.enabled && (report.interactive_quiz.options?.length ?? 0) > 0;
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => sendReply('Next', hasQuiz ? 'question' : 'tips')}
          >
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'question') {
      const quiz = report?.interactive_quiz;
      if (quiz?.options?.length) {
        return null;
      }
      return (
        <div className="chat-replies">
          <button type="button" className="chat-reply chat-reply--primary" onClick={() => sendReply('Next', 'tips')}>
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'quiz_result') {
      return (
        <div className="chat-replies">
          <button type="button" className="chat-reply chat-reply--primary" onClick={() => sendReply('Next', 'learning')}>
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'learning') {
      return (
        <div className="chat-replies">
          <button type="button" className="chat-reply chat-reply--primary" onClick={() => sendReply('Next', 'tips')}>
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'tips') {
      return (
        <div className="chat-replies">
          <button type="button" className="chat-reply chat-reply--primary" onClick={() => sendReply('Next', 'next_steps')}>
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'next_steps') {
      return (
        <div className="chat-replies">
          <button type="button" className="chat-reply chat-reply--primary" onClick={() => sendReply('Next', 'confirm')}>
            Next
          </button>
        </div>
      );
    }

    if (currentStep === 'confirm') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => {
              onLeaveSite?.();
              resetFlow();
            }}
          >
            Leave site
          </button>
          <button
            type="button"
            className="chat-reply chat-reply--secondary"
            onClick={() => sendReply('I want to go in', 'enter')}
          >
            I still want to go in
          </button>
        </div>
      );
    }

    if (currentStep === 'enter') {
      return (
        <>
          {persuadeLoading && (
            <div className="chat-message chat-message--fox" style={{ marginBottom: 12 }}>
              <div className="chat-fox-side">
                <div className="chat-avatar" aria-hidden>🦊</div>
              </div>
              <div className="chat-bubbles">
                <div className="chat-bubble" style={{ padding: '10px 14px' }}>
                  <span className="scoutnet-typing-indicator">
                    ScoutNet 正在輸入中 typing
                    <span className="dot" />
                    <span className="dot" />
                    <span className="dot" />
                  </span>
                </div>
              </div>
            </div>
          )}
          <div className="chat-reply-input-wrap">
            <textarea
              className="chat-reply-textarea"
              placeholder="e.g. I need to check something for school (required)"
              value={enterReason}
              onChange={(e) => setEnterReason(e.target.value)}
              rows={3}
              disabled={persuadeLoading}
            />
          </div>
          <div className="chat-replies">
            <button
              type="button"
              className="chat-reply chat-reply--primary"
              onClick={onSubmitReason}
              disabled={!enterReason.trim() || persuadeLoading}
              style={{ opacity: enterReason.trim() && !persuadeLoading ? 1 : 0.6 }}
            >
              Submit
            </button>
            <button
              type="button"
              className="chat-reply chat-reply--secondary"
              onClick={() => setCurrentStep('confirm')}
              disabled={persuadeLoading}
            >
              Back
            </button>
          </div>
        </>
      );
    }

    if (currentStep === 'persuade_result') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => {
              onLeaveSite?.();
              resetFlow();
            }}
          >
            Leave site
          </button>
          <button
            type="button"
            className="chat-reply chat-reply--secondary"
            onClick={() => {
              if (onProceedToUrl) onProceedToUrl();
            }}
          >
            Confirm 前往
          </button>
        </div>
      );
    }

    return null;
  };

  const quiz = report?.interactive_quiz;
  const showQuizPopup = currentStep === 'question' && (quiz?.options?.length ?? 0) > 0;

  return (
    <div className="scoutnet-container">
      <div className="scout-card">
        <header className="scout-card-header">
          <div className="scout-fox-mascot">
            <span className="scout-fox-emoji" aria-hidden>🦊</span>
          </div>
          <h1 className="scout-card-title">ScoutNet</h1>
          <p className="scout-card-subtitle">Little Fox keeps you safe</p>
        </header>
        <div className="scout-card-body">
          <div className="chat-thread" ref={threadRef}>
            <div className="chat-thread-inner">
              {conversation.map((entry, i) => (
                <React.Fragment key={i}>
                  {renderFoxBubbles(entry.step)}
                  {renderUserBubble(entry.userReply)}
                </React.Fragment>
              ))}
              {renderFoxBubbles(currentStep)}
              {renderReplyInput()}
            </div>
          </div>
        </div>
      </div>

      {showQuizPopup && quiz?.options && (
        <div
          className="scoutnet-quiz-popup-overlay"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 10000,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            boxSizing: 'border-box',
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="quiz-popup-title"
        >
          <div
            className="scoutnet-quiz-popup"
            style={{
              background: '#fff',
              borderRadius: 16,
              maxWidth: 440,
              width: '100%',
              maxHeight: '90vh',
              overflow: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
              padding: 24,
            }}
          >
            <h2 id="quiz-popup-title" style={{ margin: '0 0 12px', fontSize: 18, fontWeight: 600 }}>
              Quick question
            </h2>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.5, color: '#334155' }}>
              {quiz.question ?? 'If you accidentally open an unsuitable site, what should you do first?'}
            </p>
            {quiz.hint && (
              <p style={{ margin: '8px 0 16px', fontSize: 13, color: '#64748b' }}>{quiz.hint}</p>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {quiz.options.map((opt) => {
                const label = opt.text ?? opt.id ?? '';
                return (
                  <button
                    key={opt.id ?? opt.text}
                    type="button"
                    className="chat-reply"
                    style={{ width: '100%', textAlign: 'left', justifyContent: 'flex-start' }}
                    onClick={() => {
                      setSelectedQuizExplanation(opt.explanation ?? null);
                      sendReply(label, 'quiz_result');
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ScoutNet;
