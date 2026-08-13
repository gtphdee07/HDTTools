import { useState } from 'react';
import type { HistoryEntry, Rig, Screen, WizardState } from './types';
import { MODULES, initialHistory, initialRigs, initialWizard } from './mockData';
import { breakdown, verdictFor } from './calc';
import { Header } from './components/Header';
import { StepPills } from './components/StepPills';
import { Dashboard } from './screens/Dashboard';
import { History } from './screens/History';
import { RigStep } from './wizard/RigStep';
import { UploadStep } from './wizard/UploadStep';
import { ProcessingStep } from './wizard/ProcessingStep';
import { ReviewStep } from './wizard/ReviewStep';
import { ResultsStep } from './wizard/ResultsStep';

function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [rigs] = useState<Rig[]>(initialRigs);
  const [history] = useState<HistoryEntry[]>(initialHistory);
  const [wizard, setWizard] = useState<WizardState>(initialWizard);

  const goHome = () => setScreen('home');
  const goHistory = () => setScreen('history');

  const startWizard = () => {
    setScreen('wizard');
    setWizard((w) => ({ ...w, step: 0, subStep: 'upload' }));
  };
  const restart = startWizard;

  const selectRig = (id: string) => setWizard((w) => ({ ...w, rigChoice: id }));
  const confirmRig = () => setWizard((w) => ({ ...w, step: 1, subStep: 'upload' }));

  const simulateUpload = () => {
    setWizard((w) => ({ ...w, subStep: 'processing' }));
    setTimeout(() => setWizard((w) => ({ ...w, subStep: 'review' })), 1100);
  };

  const continueReview = () => {
    setWizard((w) => {
      const nextStep = w.step + 1;
      return { ...w, step: nextStep, subStep: nextStep === 4 ? 'review' : 'upload' };
    });
  };

  const updateField = (moduleKey: 'truck' | 'trailer' | 'scale', fieldName: string, isNumber: boolean, raw: string) => {
    const value = isNumber ? (raw === '' ? undefined : parseFloat(raw)) : raw;
    setWizard((w) => ({ ...w, [moduleKey]: { ...w[moduleKey], [fieldName]: value } }));
  };

  const step = wizard.step;
  const isWizard = screen === 'wizard';
  const isRigStep = isWizard && step === 0;
  const isUploadStep = isWizard && step >= 1 && step <= 3 && wizard.subStep === 'upload';
  const isProcessingStep = isWizard && step >= 1 && step <= 3 && wizard.subStep === 'processing';
  const isReviewStep = isWizard && step >= 1 && step <= 3 && wizard.subStep === 'review';
  const isResultsStep = isWizard && step === 4;
  const currentModule = step >= 1 && step <= 3 ? MODULES[step as 1 | 2 | 3] : null;

  const breakdownItems = isResultsStep ? breakdown(wizard.truck, wizard.trailer, wizard.scale) : [];
  const verdict = isResultsStep ? verdictFor(breakdownItems) : null;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-page)', fontFamily: 'var(--font-body)', color: 'var(--fg-1)', paddingBottom: 80 }}>
      <Header screen={screen} onGoHome={goHome} onGoHistory={goHistory} onStartWizard={startWizard} />

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

            {isUploadStep && currentModule && <UploadStep module={currentModule} onExtract={simulateUpload} />}

            {isProcessingStep && currentModule && <ProcessingStep title={currentModule.title} />}

            {isReviewStep && currentModule && (
              <ReviewStep
                module={currentModule}
                data={wizard[currentModule.key] as Record<string, unknown>}
                onFieldChange={(name, isNumber, value) => updateField(currentModule.key, name, isNumber, value)}
                onContinue={continueReview}
              />
            )}

            {isResultsStep && verdict && (
              <ResultsStep verdict={verdict} breakdownItems={breakdownItems} onRestart={restart} onGoHome={goHome} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
