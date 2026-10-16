import { useEffect, useRef, useState } from 'react';
import type { HistoryEntry, RecentRig, Screen, WizardState } from './types';
import { MODULES } from './mockData';
import { extractScaleTicket, extractTrailerTag, extractTruckTag } from './api';
import type { ScanContext } from './api';
import { ScanError, needsDifferentPhoto, photoRefused } from './scanError';
import { ScanAttempts } from './scanAttempts';
import { useScanAccess } from './scanAccess';
import type { ScanAccess } from './scanAccess';
import { useBilling } from './billing';
import { createBreakdown } from './breakdown';
import type { CreateBreakdownResult } from './breakdown';
import { useGarage } from './garage';
import type { SaveRigOutcome } from './garage';
import { useRigImport } from './garageImport';
import { RigImportBanner } from './components/RigImportBanner';
import { DisclaimerModal } from './components/DisclaimerModal';
import { Header } from './components/Header';
import { Footer } from './components/Footer';
import { StepPills } from './components/StepPills';
import { Dashboard } from './screens/Dashboard';
import { History } from './screens/History';
import { Account } from './screens/Account';
import { useAuth } from './auth';
import { RigStep } from './wizard/RigStep';
import { UploadStep } from './wizard/UploadStep';
import { ProcessingStep } from './wizard/ProcessingStep';
import { ReviewStep } from './wizard/ReviewStep';
import { ResultsStep } from './wizard/ResultsStep';

const DISCLAIMER_KEY = 'rigcheck:disclaimerAcknowledged';

const EMPTY_WIZARD: WizardState = {
  step: 0,
  subStep: 'upload',
  rigNickname: '',
  truck: {},
  trailer: {},
  scale: {},
  pendingFile: null,
  uploadError: null,
  uploadErrorCode: null,
  pinWeightPct: 20,
};

function garageNoticeFor(nickname: string, outcome: SaveRigOutcome): string | null {
  if (outcome.status === 'full') {
    const limit = outcome.cap === null ? 'is full' : `is full (the Free plan holds ${outcome.cap} Rigs)`;
    return `Your Garage ${limit}, so "${nickname}" wasn't saved to it. Your check is not affected.`;
  }
  if (outcome.status === 'failed') {
    return `We couldn't save "${nickname}" to your Garage. Your check is not affected.`;
  }
  return null;
}

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const { rigs: recentRigs, saveRig, canDeleteRig, deleteRig, refresh: refreshGarage } = useGarage();
  const [garageNotice, setGarageNotice] = useState<string | null>(null);
  const rigImport = useRigImport(refreshGarage);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [wizard, setWizard] = useState<WizardState>(EMPTY_WIZARD);
  const [checkResult, setCheckResult] = useState<CreateBreakdownResult | null>(null);
  const [disclaimerAcknowledged, setDisclaimerAcknowledged] = useState(
    () => sessionStorage.getItem(DISCLAIMER_KEY) === 'true',
  );

  const acknowledgeDisclaimer = () => {
    sessionStorage.setItem(DISCLAIMER_KEY, 'true');
    setDisclaimerAcknowledged(true);
  };

  const { recovering, linkProblem, accessToken, signOut } = useAuth();
  const billing = useBilling();
  // The account token the Scan service last refused. While it is still the token in use, scanning with it
  // would be refused again, so the visitor is offered signing in again instead of a scan.
  const [refusedToken, setRefusedToken] = useState<string | null>(null);
  const baseScanAccess = useScanAccess();
  const scanAccess: ScanAccess =
    baseScanAccess.kind === 'ready' && refusedToken !== null && refusedToken === accessToken
      ? { kind: 'sign-in-again' }
      : baseScanAccess;
  const scanAttempts = useRef(new ScanAttempts());
  // Which check is current: a new one every time a check starts. A scan notes it when it starts and drops
  // its result if the check has changed by the time the answer comes back.
  const currentCheck = useRef(0);
  // How many scans are waiting on the service. While there is one, the check cannot be left or restarted.
  const [scansInFlight, setScansInFlight] = useState(0);
  const scanning = scansInFlight > 0;
  // True while the Account screen was opened from a scan prompt in the wizard, so it can lead back to the check.
  const [accountFromWizard, setAccountFromWizard] = useState(false);
  // A password-reset email link lands the visitor here; take them straight to the new-password form.
  // An email link that could not sign them in goes to the same screen, which says why.
  useEffect(() => {
    if (recovering || linkProblem) setScreen('account');
  }, [recovering, linkProblem]);

  const goHome = () => {
    setAccountFromWizard(false);
    setScreen('home');
  };
  const goHistory = () => {
    setAccountFromWizard(false);
    setScreen('history');
  };
  const goAccount = () => {
    setAccountFromWizard(false);
    setScreen('account');
  };
  const goAccountFromWizard = () => {
    setAccountFromWizard(true);
    setScreen('account');
  };
  const backToWizard = () => {
    setAccountFromWizard(false);
    setScreen('wizard');
    // The refusal that sent the visitor to sign in again is settled either way: signed in, the scan gate is
    // clear; not signed in, the gate says so. Its message would only be stale.
    setWizard((w) => (w.uploadErrorCode === 'unauthorized' ? { ...w, uploadError: null, uploadErrorCode: null } : w));
  };
  // The Account screen only offers the sign-in form to someone who is signed out, so a refused session is
  // ended first.
  const signInAgain = async () => {
    try {
      await signOut();
    } catch {
      // Still go to the Account screen: it shows whatever state the session is really in.
    }
    goAccountFromWizard();
  };

  const startWizard = () => {
    refreshGarage();
    setGarageNotice(null);
    setAccountFromWizard(false);
    setScreen('wizard');
    setCheckResult(null);
    currentCheck.current += 1;
    setWizard(EMPTY_WIZARD);
  };
  const restart = startWizard;

  const selectExistingRig = (rig: RecentRig) =>
    setWizard((w) => ({
      ...w,
      rigNickname: rig.nickname,
      truck: rig.truck,
      trailer: rig.trailer,
      step: 3,
      subStep: 'upload',
    }));

  const startNewRig = (nickname: string) =>
    setWizard((w) => ({ ...w, rigNickname: nickname, step: 1, subStep: 'upload' }));

  const onFileSelected = (file: File) =>
    setWizard((w) => ({ ...w, pendingFile: file, uploadError: null, uploadErrorCode: null }));

  const step = wizard.step;
  const currentModule = step >= 1 && step <= 3 ? MODULES[step as 1 | 2 | 3] : null;

  // One scan through the shared Scan service, which spends a Scan Credit before reading the photo and
  // refunds it if nothing is read. Whatever the outcome, the balance on screen is read again.
  const scan = async <T,>(file: File, call: (file: File, context: ScanContext) => Promise<T>): Promise<T> => {
    if (!accessToken) throw new ScanError('unauthorized', 'Sign in to scan.');
    setScansInFlight((n) => n + 1);
    try {
      const fields = await scanAttempts.current.run(file, (clientRequestId) => call(file, { accessToken, clientRequestId }));
      void billing.refreshScanBalance();
      return fields;
    } catch (err) {
      // The service saying none are left is believed even if reading the balance back fails.
      const noneLeft = err instanceof ScanError && err.code === 'insufficient_credits';
      void billing.refreshScanBalance(noneLeft ? 0 : undefined);
      if (err instanceof ScanError && err.code === 'unauthorized') setRefusedToken(accessToken);
      throw err;
    } finally {
      setScansInFlight((n) => n - 1);
    }
  };

  const extractCurrent = async () => {
    if (!wizard.pendingFile || !currentModule) return;
    const moduleKey = currentModule.key;
    const file = wizard.pendingFile;
    const check = currentCheck.current;
    setWizard((w) => ({ ...w, subStep: 'processing' }));
    try {
      const extracted =
        moduleKey === 'truck'
          ? await scan(file, extractTruckTag)
          : moduleKey === 'trailer'
            ? await scan(file, extractTrailerTag)
            : await scan(file, extractScaleTicket);
      // The scan was paid for, but the check it was for is gone: the new one is left as it is.
      if (check !== currentCheck.current) return;
      setWizard((w) => ({ ...w, [moduleKey]: extracted, subStep: 'review', pendingFile: null }));
    } catch (err) {
      if (check !== currentCheck.current) return;
      const code = err instanceof ScanError ? err.code : null;
      setWizard((w) => ({
        ...w,
        subStep: 'error',
        uploadError: err instanceof Error ? err.message : 'Could not read that photo — try again.',
        uploadErrorCode: code,
        // A photo that was refused is not kept ready to send again: only a different one can work.
        // (After 'unauthorized' it is kept: once the user has signed in again the same photo is fine.)
        pendingFile: code && photoRefused(code) ? null : w.pendingFile,
      }));
    }
  };

  // "I don't have this image" - skip extraction entirely and go straight
  // to the review form. ReviewStep already renders {} as all-blank
  // inputs (the same path a real empty-OCR-result already takes), so no
  // change needed there.
  const skipCurrent = () => {
    if (!currentModule) return;
    const moduleKey = currentModule.key;
    setWizard((w) => ({ ...w, [moduleKey]: {}, subStep: 'review', pendingFile: null, uploadError: null, uploadErrorCode: null }));
  };

  // Reuses the scale-ticket OCR pipeline for a tow-vehicle-only ticket -
  // same CAT ticket format, just without a trailer-axle line - and maps
  // its reading onto the existing standalone_weight_lb field rather than
  // introducing a new one.
  const scanStandaloneTicket = async (file: File) => {
    const check = currentCheck.current;
    let extracted;
    try {
      extracted = await scan(file, extractScaleTicket);
    } catch (err) {
      // A failure for a check that is gone is not the new check's to show.
      if (check !== currentCheck.current) return;
      throw err;
    }
    // Returning quietly for a check that is gone is safe: the Truck review step that asked is unmounted with it.
    if (check !== currentCheck.current) return;
    const standalone =
      extracted.steer_axle_lb != null && extracted.drive_axle_lb != null
        ? extracted.steer_axle_lb + extracted.drive_axle_lb
        : extracted.gross_weight_lb;
    if (standalone == null) {
      // The service delivered, so this Scan was charged (see Scan Proxy's CONTEXT.md); a retry is a new one.
      throw new ScanError(
        'no_weight',
        "We read the ticket but couldn't find a weight. That Scan was used, and trying again uses another. You can also type the weight in.",
      );
    }
    setWizard((w) => ({ ...w, truck: { ...w.truck, standalone_weight_lb: standalone } }));
  };

  const updatePinWeightPct = (value: number) => setWizard((w) => ({ ...w, pinWeightPct: value }));

  const continueReview = async () => {
    const nextStep = wizard.step + 1;
    if (nextStep !== 4) {
      setWizard((w) => ({ ...w, step: nextStep, subStep: 'upload', pendingFile: null, uploadError: null, uploadErrorCode: null }));
      return;
    }

    setWizard((w) => ({ ...w, subStep: 'finalizing' }));
    try {
      const result = createBreakdown(wizard.truck, wizard.trailer, wizard.scale, wizard.pinWeightPct);
      setCheckResult(result);
      const nickname = wizard.rigNickname;
      void saveRig(nickname, wizard.truck, wizard.trailer).then((outcome) => setGarageNotice(garageNoticeFor(nickname, outcome)));
      setHistory((h) => [
        {
          id: crypto.randomUUID(),
          date: result.date,
          rigNickname: wizard.rigNickname,
          verdict: result.verdict,
        },
        ...h,
      ]);
      setWizard((w) => ({ ...w, step: 4, subStep: 'review' }));
    } catch (err) {
      setWizard((w) => ({
        ...w,
        subStep: 'review',
        uploadError: err instanceof Error ? err.message : 'Could not compute this check — try again.',
      }));
    }
  };

  const updateField = (moduleKey: 'truck' | 'trailer' | 'scale', fieldName: string, isNumber: boolean, raw: string) => {
    const value = isNumber ? (raw === '' ? undefined : parseFloat(raw)) : raw;
    setWizard((w) => ({ ...w, [moduleKey]: { ...w[moduleKey], [fieldName]: value } }));
  };

  const isWizard = screen === 'wizard';
  const isRigStep = isWizard && step === 0;
  const isUploadStep =
    isWizard && step >= 1 && step <= 3 && (wizard.subStep === 'upload' || wizard.subStep === 'error');
  const isProcessingStep =
    isWizard && step >= 1 && step <= 3 && (wizard.subStep === 'processing' || wizard.subStep === 'finalizing');
  const isReviewStep = isWizard && step >= 1 && step <= 3 && wizard.subStep === 'review';
  const isResultsStep = isWizard && step === 4 && checkResult !== null;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', fontFamily: 'var(--font-body)', color: 'var(--fg-1)', paddingBottom: 80 }}>
      <Header
        screen={screen}
        onGoHome={goHome}
        onGoHistory={goHistory}
        onStartWizard={startWizard}
        onGoAccount={goAccount}
        locked={scanning}
      />

      <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '36px 32px' }}>
        <RigImportBanner rigImport={rigImport} />
        {garageNotice && (
          <div
            role="status"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              background: 'var(--color-tint-purple)',
              color: 'var(--fg-1)',
              borderRadius: 12,
              padding: '12px 16px',
              marginBottom: 20,
              fontSize: 14,
            }}
          >
            <span style={{ flex: 1 }}>{garageNotice}</span>
            <button
              onClick={() => setGarageNotice(null)}
              style={{ background: 'none', border: 'none', color: 'var(--fg-2)', cursor: 'pointer', fontSize: 13 }}
            >
              Dismiss
            </button>
          </div>
        )}
        {screen === 'home' && (
          <Dashboard
            recentRigs={recentRigs}
            history={history}
            onStartWizard={startWizard}
            onGoHistory={goHistory}
            onDeleteRig={canDeleteRig ? deleteRig : undefined}
          />
        )}
        {screen === 'history' && <History history={history} recentRigs={recentRigs} />}
        {screen === 'account' && (
          <Account
            onDone={accountFromWizard ? backToWizard : goHome}
            doneLabel={accountFromWizard ? 'Back to your check' : undefined}
          />
        )}

        {isWizard && (
          <div>
            <button
              onClick={goHome}
              disabled={scanning}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--fg-2)',
                fontSize: 13,
                cursor: scanning ? 'not-allowed' : 'pointer',
                opacity: scanning ? 0.5 : 1,
                padding: 0,
                marginBottom: scanning ? 6 : 14,
              }}
            >
              &larr; Back to Dashboard
            </button>
            {scanning && (
              <div role="status" style={{ color: 'var(--fg-2)', fontSize: 13, marginBottom: 14 }}>
                Reading your photo&hellip; you can leave this check once it's done.
              </div>
            )}

            <StepPills step={step} />

            {isRigStep && (
              <RigStep
                recentRigs={recentRigs}
                onSelectExisting={selectExistingRig}
                onStartNew={startNewRig}
                onDeleteRig={canDeleteRig ? deleteRig : undefined}
              />
            )}

            {isUploadStep && currentModule && (
              <UploadStep
                module={currentModule}
                file={wizard.pendingFile}
                error={wizard.uploadError}
                scanAccess={scanAccess}
                needsNewPhoto={wizard.uploadErrorCode !== null && needsDifferentPhoto(wizard.uploadErrorCode)}
                onGoAccount={scanAccess.kind === 'sign-in-again' ? signInAgain : goAccountFromWizard}
                onRetryScanAccess={billing.reload}
                onFileSelected={onFileSelected}
                onExtract={extractCurrent}
                onSkip={skipCurrent}
              />
            )}

            {isProcessingStep && (
              <ProcessingStep title={wizard.subStep === 'finalizing' ? 'your results' : (currentModule?.title ?? '')} />
            )}

            {isReviewStep && currentModule && (
              <ReviewStep
                module={currentModule}
                data={wizard[currentModule.key] as Record<string, unknown>}
                error={wizard.uploadError}
                onFieldChange={(name, isNumber, value) => updateField(currentModule.key, name, isNumber, value)}
                onContinue={continueReview}
                {...(currentModule.key === 'truck'
                  ? {
                      pinWeightPct: wizard.pinWeightPct,
                      onPinWeightPctChange: updatePinWeightPct,
                      onScanStandaloneTicket: scanStandaloneTicket,
                      scanAccess,
                      onGoAccount: scanAccess.kind === 'sign-in-again' ? signInAgain : goAccountFromWizard,
                      onRetryScanAccess: billing.reload,
                    }
                  : {})}
              />
            )}

            {isResultsStep && checkResult && !disclaimerAcknowledged && (
              <DisclaimerModal onAcknowledge={acknowledgeDisclaimer} />
            )}

            {isResultsStep && checkResult && disclaimerAcknowledged && (
              <ResultsStep
                verdict={checkResult.verdictInfo}
                breakdownItems={checkResult.breakdownItems}
                onRestart={restart}
                onGoHome={goHome}
              />
            )}
          </div>
        )}
      </div>

      <Footer onGoHome={goHome} onGoHistory={goHistory} locked={scanning} />
    </div>
  );
}

export default App;
