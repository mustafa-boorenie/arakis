import { Composition } from 'remotion';
import { ArakisWorkflow } from './ArakisWorkflow';
import { TimeSaverVideo } from './variations/TimeSaverVideo';
import { CostEffectiveVideo } from './variations/CostEffectiveVideo';
import { AcademicVideo } from './variations/AcademicVideo';
import {
  MobileArakisWorkflow,
  MobileTimeSaver,
  MobileCostEffective,
  MobileAcademic,
} from './mobile/MobileCompositions';

export const Root: React.FC = () => {
  return (
    <>
      {/* ========== DESKTOP (1920x1080) ========== */}

      {/* Original video */}
      <Composition
        id="ArakisWorkflow"
        component={ArakisWorkflow}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* Variation 1: Time-Saver Hook */}
      <Composition
        id="TimeSaver"
        component={TimeSaverVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* Variation 2: Cost-Effective Hook */}
      <Composition
        id="CostEffective"
        component={CostEffectiveVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* Variation 3: Academic Excellence Hook */}
      <Composition
        id="Academic"
        component={AcademicVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* ========== MOBILE (1080x1920) ========== */}

      {/* Mobile Original */}
      <Composition
        id="MobileArakisWorkflow"
        component={MobileArakisWorkflow}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Mobile Time-Saver */}
      <Composition
        id="MobileTimeSaver"
        component={MobileTimeSaver}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Mobile Cost-Effective */}
      <Composition
        id="MobileCostEffective"
        component={MobileCostEffective}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
      />

      {/* Mobile Academic */}
      <Composition
        id="MobileAcademic"
        component={MobileAcademic}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
