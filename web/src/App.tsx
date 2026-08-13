import { useEffect, useState } from 'react';
import type { HistoryEntry, Rig, Screen, WizardState } from './types';
import { MODULES } from './mockData';
import {
  createCheck,
  extractScaleTicket,
  extractTrailerTag,
  extractTruckTag,
  fetchHistory,
  fetchRigs,
} from './api';
import type { CreateCheckResult } from './api';
import { Header } from './components/Header';
import { StepPills } from './components/StepPills';
import { Dashboard } from './screens/Dashboard';
import { History } from './screens/History';
import { RigStep } from './wizard/RigStep';
import { UploadStep } from './wizard/UploadStep';
import { ProcessingStep } from './wizard/ProcessingStep';
import { ReviewStep } from './wizard/ReviewStep';
import { ResultsStep } from './wizard/ResultsStep';

const EMPTY_WIZARD: WizardState = {
  step: 0,
  subStep: 'upload',
  rigChoice: '',
  truck: {},
  trailer: {},
  scale: {},
  pendingFile: null,
  uploadError: null,
};

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [rigs, setRigs] = useState<Rig[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [wizard, setWizard] = useState<WizardState>(EMPTY_WIZARD);
  const [checkResult, setCheckResult] = useState<CreateCheckResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([fetchRigs(), fetchHistory()])
      .then(([loadedRigs, loadedHistory]) => {
        setRigs(loadedRigs);
        setHistory(loadedHistory);
        setWizard((w) => (w.rigChoice ? w : { ...w, rigChoice: loadedRigs[0]?.id ?? '' }));
      })
      .catch((err) => setLoadError(err instanceof Error ? err.message : 'Failed to reach the backend.'));
  }, []);

  const goHome = () => setScreen('home');
  const goHistory = () => setScreen('history');

  const startWizard = () => {
    setScreen('wizard');
    setCheckResult(null);
    setWizard((w) => ({
      ...w,
      step: 0,
      subStep: 'upload',
      truck: {},
      trailer: {},
      scale: {},
      pendingFile: null,
      uploadError: null,
    }));
  };
  const restart = startWizard;

  const selectRig = (id: string) => setWizard((w) => ({ ...w, rigChoice: id }));
  const confirmRig = () => setWizard((w) => ({ ...w, step: 1, subStep: 'upload' }));

  const onFileSelected = (file: File) => setWizard((w) => ({ ...w, pendingFile: file, uploadError: null }));

  const step = wizard.step;
  const currentModule = step >= 1 && step <= 3 ? MODULES[step as 1 | 2 | 3] : null;

  const extractCurrent = async () => {
    if (!wizard.pendingFile || !currentModule) return;
    const moduleKey = currentModule.key;
    const file = wizard.pendingFile;
    setWizard((w) => ({ ...w, subStep: 'processing' }));
    try {
      const extracted =
        moduleKey === 'truck'
          ? await extractTruckTag(file)
          : moduleKey === 'trailer'
            ? await extractTrailerTag(file)
            : await extractScaleTicket(file);
      setWizard((w) => ({ ...w, [moduleKey]: extracted, subStep: 'review', pendingFile: null }));
    } catch (err) {
      setWizard((w) => ({
        ...w,
        subStep: 'error',
        uploadError: err instanceof Error ? err.message : 'Could not read that photo — try again.',
      }));
    }
  };

  const continueReview = async () => {
    const nextStep = wizard.step + 1;
    if (nextStep !== 4) {
      setWizard((w) => ({ ...w, step: nextStep, subStep: 'upload', pendingFile: null, uploadError: null }));
      return;
    }

    setWizard((w) => ({ ...w, subStep: 'finalizing' }));
    try {
      const result = await createCheck(wizard.rigChoice, wizard.truck, wizard.trailer, wizard.scale);
      setCheckResult(result);
      const rig = rigs.find((r) => r.id === wizard.rigChoice);
      if (rig) {
        setHistory((h) => [
          {
            id: result.id,
            date: result.date,
            truckName: rig.truckName,
            trailerName: rig.trailerName,
            verdict: result.verdict,
          },
          ...h,
        ]);
      }
      setWizard((w) => ({ ...w, step: 4, subStep: 'review' }));
    } catch (err) {
      setWizard((w) => ({
        ...w,
        subStep: 'review',
        uploadError: err instanceof Error ? err.message : 'Could not save this check — try again.',
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
      <Header screen={screen} onGoHome={goHome} onGoHistory={goHistory} onStartWizard={startWizard} />

      {loadError && (
        <div style={{ background: 'var(--state-danger)', color: '#fff', padding: '10px 32px', fontSize: 13 }}>
          {loadError} — is the backend running at http://localhost:8000?
        </div>
      )}

      <div style={{ maxWidth: 'var(--container-max)', margin: '0 auto', padding: '36px 32px' }}>
        {screen === 'home' && <Dashboard rigs={rigs} history={history} onStartWizard={startWizard} />}
        {screen === 'history' && <History history={history} />}

        {isWizard && (
          <div>
            <button
              onClick={goHome}
              style={{ background: 'none', border: 'none', color: 'var(--fg-2)', fontSize: 13, cursor: 'pointer', padding: 0, marginBottom: 14 }}
            >
              &larr; Back to Dashboard
            </button>

            <StepPills step={step} />

            {isRigStep && (
              <RigStep rigs={rigs} rigChoice={wizard.rigChoice} onSelect={selectRig} onConfirm={confirmRig} />
            )}

            {isUploadStep && currentModule && (
              <UploadStep
                module={currentModule}
                file={wizard.pendingFile}
                error={wizard.uploadError}
                onFileSelected={onFileSelected}
                onExtract={extractCurrent}
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
              />
            )}

            {isResultsStep && checkResult && (
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
    </div>
  );
}

export default App;
