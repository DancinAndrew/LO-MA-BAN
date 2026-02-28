import React, { useState, useRef, useEffect } from 'react';
import '../styles/ScoutNet.css';
import { getDefaultSiteData, type SiteData } from '../siteDetection';

type Step =
  | 'rating'
  | 'question'
  | 'reasons'
  | 'correct'
  | 'wrong'
  | 'enter'
  | 'final';

type ConversationEntry = { step: Step; userReply: string };

const REASONS = [
  { id: 'url', text: 'The URL is wrong' },
  { id: 'password', text: 'It asked for my password suddenly' },
  { id: 'design', text: 'The site looks weird' },
  { id: 'other', text: 'Something else' },
] as const;

export type ScoutNetProps = {
  /** 從偵測模組或擴充腳本傳入的網站資料；不傳則用預設展示資料 */
  siteData?: SiteData | null;
  /** 在擴充警告頁時：點「Leave site」會呼叫此 callback，回到上一頁 */
  onLeaveSite?: () => void;
  /** 在擴充警告頁時：點「I still want to go in」會呼叫此 callback，前往風險網站 */
  onProceedToUrl?: () => void;
};

const ScoutNet: React.FC<ScoutNetProps> = ({ siteData: siteDataProp, onLeaveSite, onProceedToUrl }) => {
  const [currentStep, setCurrentStep] = useState<Step>('rating');
  const [conversation, setConversation] = useState<ConversationEntry[]>([]);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [enterReason, setEnterReason] = useState('');
  const threadRef = useRef<HTMLDivElement>(null);

  const siteData: SiteData = siteDataProp ?? getDefaultSiteData();

  const scrollToBottom = () => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight, behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation, currentStep]);

  const resetFlow = () => {
    setCurrentStep('rating');
    setConversation([]);
    setSelectedReasons([]);
    setEnterReason('');
  };

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
              <p className="chat-bubble-text">I checked this link — it looks risky. Here’s what I found.</p>
            </div>
            <div className="chat-bubble chat-bubble--card">
              <div className="risk-badge risk-badge--inline">
                <span className="risk-icon">⚠️</span>
                <span className="risk-level">High-risk site</span>
                <span className="risk-score">Safety {siteData.riskScore}</span>
              </div>
              <div className="url-comparison url-comparison--compact">
                <div className="url-item">
                  <span className="url-label">You're visiting</span>
                  <span className="url-current">{siteData.currentUrl}</span>
                </div>
                <div className="url-item">
                  <span className="url-label">Correct URL</span>
                  <span className="url-correct">{siteData.correctUrl ?? '—'}</span>
                </div>
              </div>
              <p className="chat-bubble-label">Suspicious things we spotted:</p>
              {siteData.warnings.map((warning, index) => (
                <div key={index} className="warning-item warning-item--compact">
                  <span className="warning-dot">{index + 1}</span>
                  <span className="warning-text">{warning}</span>
                </div>
              ))}
            </div>
          </>
        )}
        {step === 'question' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">What seems weird about this site? Tap one below.</p>
          </div>
        )}
        {step === 'reasons' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">What problems did you find? You can pick more than one.</p>
          </div>
        )}
        {step === 'correct' && (
          <>
            <div className="chat-bubble">
              <p className="chat-bubble-text">You paid great attention!</p>
            </div>
            <div className="chat-bubble chat-bubble--success">
              <span className="chat-bubble-icon">🎉</span>
              <p className="chat-bubble-text">Right! The URL typo is the main problem.</p>
            </div>
          </>
        )}
        {step === 'wrong' && (
          <>
            <div className="chat-bubble">
              <p className="chat-bubble-text">Think again ~</p>
            </div>
            <div className="chat-bubble chat-bubble--warning">
              <p className="chat-bubble-text">
                <strong>The main problem is:</strong> The URL is wrong (paypa1.com is not paypal.com).
              </p>
            </div>
          </>
        )}
        {step === 'enter' && (
          <div className="chat-bubble">
            <p className="chat-bubble-text">Why do you still want to go in? Type your reason below.</p>
          </div>
        )}
        {step === 'final' && (
          <>
            <div className="chat-bubble">
              <p className="chat-bubble-text">Be careful with this site!</p>
            </div>
            <div className="chat-bubble chat-bubble--warning">
              <p className="chat-bubble-text">You said: {enterReason || 'No reason given'}</p>
              <p className="chat-bubble-note">This site might be a scam.</p>
            </div>
            <div className="chat-bubble chat-bubble--tips">
              <p className="chat-bubble-label">🔒 Quick reminders:</p>
              <ul className="chat-bubble-list">
                <li>Never enter your real password</li>
                <li>Don't share personal info</li>
                <li>When in doubt, ask a parent</li>
              </ul>
            </div>
          </>
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
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => sendReply('Got it, tell me more', 'question')}
          >
            Got it, tell me more
          </button>
        </div>
      );
    }

    if (currentStep === 'question') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply"
            onClick={() => sendReply('I found something wrong', 'reasons')}
          >
            <span className="chat-reply-emoji">🔍</span>
            I found something wrong
          </button>
          <button type="button" className="chat-reply" onClick={() => sendReply('I think it\'s fine', 'wrong')}>
            <span className="chat-reply-emoji">✅</span>
            I think it's fine
          </button>
          <button type="button" className="chat-reply" onClick={() => sendReply('I\'m not sure', 'wrong')}>
            <span className="chat-reply-emoji">❓</span>
            I'm not sure
          </button>
        </div>
      );
    }

    if (currentStep === 'reasons') {
      const toggleReason = (id: string) => {
        setSelectedReasons((prev) =>
          prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
        );
      };
      const summary =
        selectedReasons.length > 0
          ? selectedReasons
              .map((id) => REASONS.find((r) => r.id === id)?.text ?? id)
              .join(', ')
          : '';
      return (
        <>
          <div className="chat-replies chat-replies--checklist">
            {REASONS.map((reason) => (
              <label
                key={reason.id}
                className={`chat-reply chat-reply--choice ${selectedReasons.includes(reason.id) ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={selectedReasons.includes(reason.id)}
                  onChange={() => toggleReason(reason.id)}
                  className="chat-reply-checkbox"
                />
                <span className="chat-reply-text">{reason.text}</span>
              </label>
            ))}
            {selectedReasons.includes('other') && (
              <input
                className="chat-reply-input"
                placeholder="Tell me what else..."
                value={enterReason}
                onChange={(e) => setEnterReason(e.target.value)}
              />
            )}
          </div>
          <div className="chat-replies chat-replies--actions">
            <button
              type="button"
              className="chat-reply chat-reply--primary"
              onClick={() => {
                const replyText = summary || 'Send my answer';
                if (selectedReasons.includes('url')) sendReply(replyText, 'correct');
                else sendReply(replyText, 'wrong');
              }}
            >
              Send my answer
            </button>
            <button
              type="button"
              className="chat-reply chat-reply--secondary"
              onClick={() => setCurrentStep('question')}
            >
              Back
            </button>
          </div>
        </>
      );
    }

    if (currentStep === 'correct') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => {
              onLeaveSite?.()
              resetFlow()
            }}
          >
            Leave site
          </button>
          <button
            type="button"
            className="chat-reply chat-reply--secondary"
            onClick={() => {
              if (onProceedToUrl) onProceedToUrl()
              else sendReply('I still want to go in', 'enter')
            }}
          >
            I still want to go in
          </button>
        </div>
      );
    }

    if (currentStep === 'wrong') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => sendReply('Choose again', 'reasons')}
          >
            Choose again
          </button>
          <button
            type="button"
            className="chat-reply chat-reply--secondary"
            onClick={() => resetFlow()}
          >
            Start over
          </button>
        </div>
      );
    }

    if (currentStep === 'enter') {
      return (
        <>
          <div className="chat-reply-input-wrap">
            <textarea
              className="chat-reply-textarea"
              placeholder="Tell me your reason..."
              value={enterReason}
              onChange={(e) => setEnterReason(e.target.value)}
              rows={3}
            />
          </div>
          <div className="chat-replies">
            <button
              type="button"
              className="chat-reply chat-reply--primary"
              onClick={() => sendReply(enterReason || 'Sent', 'final')}
            >
              Send
            </button>
            <button
              type="button"
              className="chat-reply chat-reply--secondary"
              onClick={() => setCurrentStep('correct')}
            >
              Back
            </button>
          </div>
        </>
      );
    }

    if (currentStep === 'final') {
      return (
        <div className="chat-replies">
          <button
            type="button"
            className="chat-reply chat-reply--primary"
            onClick={() => resetFlow()}
          >
            Got it
          </button>
        </div>
      );
    }

    return null;
  };

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
    </div>
  );
};

export default ScoutNet;
