/* Reference content. Disease names in EN/TE/HI are carried over from the
   original AstraNex interface so nothing the project already knew is lost. */
window.AX_DATA = (function () {

  const CROPS = [
    { id: 'paddy', en: 'Rice / Paddy', te: 'వరి', hi: 'धान', icon: '🌾' },
    { id: 'tomato', en: 'Tomato', te: 'టమాటో', hi: 'टमाटर', icon: '🍅' },
    { id: 'chilli', en: 'Chilli', te: 'మిర్చి', hi: 'मिर्च', icon: '🌶️' },
    { id: 'cotton', en: 'Cotton', te: 'పత్తి', hi: 'कपास', icon: '🌿' },
    { id: 'maize', en: 'Maize', te: 'మొక్కజొన్న', hi: 'मक्का', icon: '🌽' },
    { id: 'groundnut', en: 'Groundnut', te: 'వేరుశనగ', hi: 'मूंगफली', icon: '🥜' },
    { id: 'brinjal', en: 'Brinjal', te: 'వంకాయ', hi: 'बैंगन', icon: '🍆' },
    { id: 'turmeric', en: 'Turmeric', te: 'పసుపు', hi: 'हल्दी', icon: '🌱' }
  ];

  const DISEASES = [
    { crop: 'paddy', icon: '🌾', name: 'Rice Blast', te: 'వరి మెడ విరుపు తెగులు', hi: 'धान झोंका रोग',
      signs: ['Spindle-shaped lesions with grey centres on leaves', 'Neck rot at panicle base', 'Whitish panicles that fail to fill'],
      risk: ['Long leaf wetness and night humidity above 85%', 'Excess nitrogen', 'Cloudy spells at panicle initiation'],
      prevent: ['Use locally recommended resistant varieties', 'Split nitrogen instead of a single heavy dose', 'Avoid dense planting so the canopy dries'],
      monitor: 'Inspect the neck node and flag leaf every 3 days from booting.' },
    { crop: 'paddy', icon: '🌾', name: 'Bacterial Leaf Blight', te: 'బాక్టీరియా ఆకు ఎండు తెగులు', hi: 'जीवाणु पत्ती झुलसा रोग',
      signs: ['Water-soaked margins turning straw-yellow', 'Lesions running down from the leaf tip', 'Milky bacterial ooze in the morning'],
      risk: ['Standing water after storms', 'Wounding during transplanting', 'High nitrogen with high humidity'],
      prevent: ['Drain excess water where drainage exists', 'Avoid clipping seedling tips', 'Remove infected stubble between seasons'],
      monitor: 'Check field entry points and low-lying corners after every heavy rain.' },
    { crop: 'tomato', icon: '🍅', name: 'Early Blight', te: 'తొలిదశ ఆకుమచ్చ తెగులు (ఎర్లీ బ్లైట్)', hi: 'अगेती झुलसा (अर्ली ब्लाइट)',
      signs: ['Concentric dark rings on older leaves', 'Yellow halo around each lesion', 'Defoliation moving up from the base'],
      risk: ['Alternating wet and dry spells', 'Temperatures 24–29 °C with leaf wetness', 'Stressed or fruit-heavy plants'],
      prevent: ['Remove affected lower leaves from the field', 'Mulch to stop soil splash', 'Stake for airflow and avoid overhead watering'],
      monitor: 'Check the lowest three leaves of ten plants twice a week.' },
    { crop: 'tomato', icon: '🍅', name: 'Tomato Yellow Leaf Curl Virus', te: 'పసుపు ఆకు ముడత వైరస్', hi: 'पीला पत्ता मोड़ विषाणु',
      signs: ['Upward curling, cupped young leaves', 'Stunted growth with short internodes', 'Flower drop and poor fruit set'],
      risk: ['Whitefly pressure', 'Nearby infected crops or volunteers', 'Hot dry periods that favour the vector'],
      prevent: ['Manage whitefly using locally approved integrated pest management', 'Use virus-free seedlings', 'Remove volunteer hosts near the field'],
      monitor: 'Turn over young leaves and count whitefly adults on ten plants weekly.' },
    { crop: 'chilli', icon: '🌶️', name: 'Cercospora Leaf Spot', te: 'సర్కోస్పోరా ఆకుమచ్చ తెగులు', hi: 'सर्कोस्पोरा पत्ती धब्बा रोग',
      signs: ['Round spots with pale centres and dark margins', 'Frog-eye appearance on mature leaves', 'Premature leaf fall'],
      risk: ['Extended humid weather', 'Dense canopy with poor airflow', 'Overhead irrigation late in the day'],
      prevent: ['Space plants for drying airflow', 'Irrigate early so foliage dries', 'Clear crop residue between seasons'],
      monitor: 'Sample mid-canopy leaves across the block every 4–5 days in humid spells.' },
    { crop: 'chilli', icon: '🌶️', name: 'Chilli Leaf Curl Virus', te: 'మిర్చి ఆకు ముడత వైరస్', hi: 'मिर्च पत्ती मोड़ विषाणु',
      signs: ['Curling and puckering of young leaves', 'Shortened internodes, bushy appearance', 'Reduced fruit size and set'],
      risk: ['High whitefly activity', 'Continuous chilli cropping', 'Dry warm conditions'],
      prevent: ['Vector management through locally approved IPM', 'Rogue severely affected plants early', 'Use healthy nursery material'],
      monitor: 'Scout nursery and first 30 days after transplanting twice weekly.' },
    { crop: 'cotton', icon: '🌿', name: 'Grey Mildew', te: 'బూడిద బూజు తెగులు', hi: 'धूसर फफूंदी',
      signs: ['Angular pale lesions bounded by veins', 'Powdery growth on the underside', 'Early leaf shed in severe cases'],
      risk: ['Cool nights with heavy dew', 'Dense canopy', 'Late-season crop stress'],
      prevent: ['Balanced nutrition rather than excess nitrogen', 'Maintain row spacing for airflow', 'Remove heavily affected leaves'],
      monitor: 'Inspect the underside of mid-canopy leaves weekly from squaring onward.' },
    { crop: 'cotton', icon: '🌿', name: 'Cotton Leaf Curl Virus', te: 'పత్తి ఆకు ముడత వైరస్', hi: 'कपास पत्ती मोड़ विषाणु',
      signs: ['Upward or downward leaf curling', 'Vein thickening and enations', 'Stunted plants with poor boll set'],
      risk: ['Whitefly build-up', 'Susceptible varieties', 'Nearby infected fields'],
      prevent: ['Use recommended tolerant varieties', 'Whitefly monitoring with yellow sticky traps', 'Avoid staggered sowing near infected blocks'],
      monitor: 'Weekly whitefly counts plus curl symptom counts on 20 plants.' },
    { crop: 'maize', icon: '🌽', name: 'Northern Leaf Blight', te: 'ఉత్తర ఆకు ఎండు తెగులు', hi: 'उत्तरी पत्ती झुलसा रोग',
      signs: ['Long cigar-shaped grey-green lesions', 'Lesions spreading upward from lower leaves', 'Blighted appearance before tasselling'],
      risk: ['Moderate temperatures with long dew periods', 'Continuous maize cropping', 'Dense stands'],
      prevent: ['Rotate away from maize where possible', 'Bury or remove infected residue', 'Choose resistant hybrids locally recommended'],
      monitor: 'Check the ear leaf and one below it weekly from knee-high stage.' },
    { crop: 'maize', icon: '🌽', name: 'Common Rust', te: 'సాధారణ కుంకుమ తెగులు', hi: 'सामान्य रतुआ रोग',
      signs: ['Cinnamon-brown pustules on both leaf surfaces', 'Pustules rupturing to release spores', 'Chlorosis around heavy pustule clusters'],
      risk: ['Cool humid weather, 16–23 °C', 'Prolonged leaf wetness', 'Late-planted crops'],
      prevent: ['Plant within the recommended window', 'Select tolerant hybrids', 'Maintain balanced nutrition'],
      monitor: 'Scan five plants per corner plus the centre of the block weekly.' },
    { crop: 'groundnut', icon: '🥜', name: 'Early Leaf Spot', te: 'తొలిదశ ఆకుమచ్చ తెగులు', hi: 'अगेती पत्ती धब्बा रोग',
      signs: ['Brown spots with yellow halos on upper surface', 'Spots enlarging and merging', 'Defoliation from the base upward'],
      risk: ['Warm humid weather after 40 days', 'Dense canopy and continuous cropping', 'Overhead irrigation'],
      prevent: ['Rotate with cereals', 'Remove volunteer groundnut plants', 'Irrigate early in the day'],
      monitor: 'Count spotted leaflets on ten plants weekly from 35 days after sowing.' },
    { crop: 'groundnut', icon: '🥜', name: 'Groundnut Rust', te: 'వేరుశనగ కుంకుమ తెగులు', hi: 'मूंगफली रतुआ रोग',
      signs: ['Orange pustules on the lower leaf surface', 'Leaves drying but staying attached', 'Reduced pod filling'],
      risk: ['High humidity with 20–30 °C', 'Late sowing', 'Continuous groundnut in the same field'],
      prevent: ['Use recommended tolerant varieties', 'Destroy crop residue', 'Avoid overlapping crop cycles'],
      monitor: 'Check the lower canopy twice weekly through pod development.' },
    { crop: 'brinjal', icon: '🍆', name: 'Phomopsis Blight', te: 'ఫోమోప్సిస్ ఎండు తెగులు', hi: 'फोमोप्सिस झुलसा रोग',
      signs: ['Grey-brown leaf spots with dark margins', 'Stem canker near the collar', 'Sunken soft rot on fruits'],
      risk: ['Warm humid weather', 'Infected seed', 'Fruit contact with wet soil'],
      prevent: ['Use healthy certified seed', 'Stake fruits away from soil contact', 'Remove and destroy infected fruits'],
      monitor: 'Inspect fruits and collar region every 3–4 days in wet weather.' },
    { crop: 'turmeric', icon: '🌱', name: 'Leaf Spot (Colletotrichum)', te: 'ఆకుమచ్చ తెగులు (కొల్లెటోట్రైకమ్)', hi: 'पत्ती धब्बा रोग (कोलेटोट्राइकम)',
      signs: ['Elliptical brown spots with pale centres', 'Spots coalescing into dried patches', 'Drying of leaf margins'],
      risk: ['Continuous rain and high humidity', 'Poor drainage', 'Dense planting'],
      prevent: ['Improve drainage before the monsoon', 'Maintain spacing and remove affected leaves', 'Rotate away from turmeric and ginger'],
      monitor: 'Check the third and fourth leaves weekly through the rainy season.' }
  ];

  const SAFETY_NOTE = 'Reference information only. AstraNex does not prescribe pesticides. Confirm identification with a local agricultural officer or RBK and follow locally approved integrated pest-management guidance before any treatment.';

  const STATUS_BADGES = [
    ['Agricultural use case', 'Defined', 'ok'],
    ['Existing vision pipeline', 'Prototype', 'ok'],
    ['Sensor integration', 'Prototype', 'ok'],
    ['Multimodal fusion', 'Prototype', 'ok'],
    ['Classical baseline', 'Implemented', 'ok'],
    ['QML circuit', 'Experimental', 'exp'],
    ['Qiskit execution', 'When available — see About for the live check', 'exp'],
    ['Model benchmarking', 'Experimental', 'exp'],
    ['Multispectral / drone integration', 'Future', 'future'],
    ['Field deployment', 'Future', 'future'],
    ['Quantum hardware validation', 'Future', 'future']
  ];

  const FLOW = [
    ['Capture', 'Crop image, soil moisture, temperature, humidity and weather context arrive from the phone and field device.'],
    ['Fuse', 'Sensor reliability and image quality weight the evidence. Weak evidence produces a verification prompt, not a diagnosis.'],
    ['Encode', 'Eight agricultural features are ranked; the strongest four are encoded onto four qubits by whichever quantum engine is active.'],
    ['Warn', 'Classical and quantum predictions are compared, and an early-warning level with a concrete next step is issued.']
  ];

  const RESEARCH = [
    { id: 'why', title: 'Why quantum machine learning here?',
      body: [
        'Crop-outbreak risk is a small-sample, high-dimensional problem. A field officer does not have a million labelled examples; they have a handful of signals per block, each noisy in a different way. Variational quantum classifiers are interesting in exactly this regime because the feature map can express correlations between features with very few trainable parameters.',
        'That is a research motivation, not a result. The Quantum lab page computes the actual comparison on this prototype\'s demonstration dataset each time it is run, and prints its own verdict; the classical model is far cheaper to run in every case. The honest statement is that the quantum layer is an experiment attached to a working agricultural system, not an improvement over it.'
      ] },
    { id: 'hybrid', title: 'How the hybrid model works',
      body: [
        'The circuit never sees raw pixels or raw sensor bytes. The existing AstraNex pipeline runs first: ONNX vision inference produces a class and a confidence, the sensor-health module produces a reliability score, and the fusion engine produces disease, water, heat and excess-water risk. Those outputs are the features.',
        'Each selected feature is normalised into [0, 1]. In the Qiskit Machine Learning path, the four values are supplied as feature parameters to a ZZFeatureMap, followed by a RealAmplitudes variational ansatz; EstimatorQNN produces the model output from the measured observable. A classical SPSA optimiser updates the trainable parameters. The optimiser is classical; the circuit evaluation is simulated quantum execution.'
      ] },
    { id: 'features', title: 'Feature engineering',
      body: [
        'Eight features are produced for every scan: disease signal, soil moisture, temperature, humidity, water risk, heat stress risk, sensor reliability and image confidence. Excess-water risk is carried alongside as context.',
        'Ranking uses the absolute Pearson correlation with the training label, scaled by feature spread, computed on the training split only. The top four reach the qubits. The full ranking is shown in the Quantum lab so the selection is auditable rather than asserted.'
      ] },
    { id: 'encoding', title: 'Quantum feature encoding',
      body: [
        'Two encodings exist in this codebase and the interface never conflates them. When Qiskit Machine Learning is installed, a ZZFeatureMap performs a second-order Pauli-Z feature encoding of the four selected features, followed by a RealAmplitudes ansatz. When it is not, a simpler custom circuit is used: each feature becomes a single RY rotation in [0, π] — angle encoding — followed by a custom RY/RZ variational block. Whichever ran for a given prediction is named exactly in the Quantum Lab and in the API response; the two are never presented as interchangeable.',
        'Angle encoding was chosen for the fallback path because, with four features and four qubits, state preparation is one rotation per qubit — shallow enough for a prototype budget, and each qubit stays interpretable as one agricultural signal. Its cost is expressiveness: it discards magnitude information beyond the rotation. ZZFeatureMap additionally captures pairwise feature interactions through its entangling ZZ terms, which angle encoding alone does not.'
      ] },
    { id: 'variational', title: 'Variational circuit and training',
      body: [
        'Four qubits and two layers. The built-in engine has sixteen circuit parameters plus five classical read-out parameters, with entanglement alternating between even and odd CX pairs around a ring so that every qubit interacts within two layers. When Qiskit Machine Learning is installed and passes its self-test, the model is instead a ZZFeatureMap followed by a RealAmplitudes ansatz (twelve trainable parameters) wrapped in an EstimatorQNN; the Quantum lab always states which one ran.',
        'Training uses SPSA with mini-batches. SPSA needs two circuit evaluations per iteration regardless of parameter count, which keeps simulator-based training practical; the loss history is recorded and displayed. Nothing is pre-baked: pressing "Run experimental benchmark" retrains both models and recomputes every number on screen.'
      ] },
    { id: 'state', title: 'Reading the quantum state',
      body: [
        'Beyond a single risk number, the Quantum lab shows what the circuit actually prepares. For every qubit it computes the reduced single-qubit state from the full state vector and draws it on a Bloch sphere. A qubit that is entangled with its neighbours has a mixed reduced state, which appears as an arrow shorter than the sphere\'s radius.',
        'Entanglement is quantified two ways: the von Neumann entropy of each qubit (0 bits for an independent qubit, 1 bit for a maximally entangled one) and the Meyer-Wallach measure for the whole register (0 to 1). Both are exact numbers derived from the simulated amplitudes.',
        'Measurement statistics are shown twice: the exact basis-state probabilities, and finite-shot counts sampled from them, which is what a real device would return with no hardware noise. The noise sweep applies a simplified global depolarising channel to the output state to show how fragile a prediction would be on noisy hardware. It is a simulation, not a hardware measurement.'
      ] },
    { id: 'comparison', title: 'Classical versus quantum',
      body: [
        'The baseline is logistic regression on the identical selected feature vector, with the identical train/test split. Accuracy, precision, recall, F1 and per-sample inference time are computed on the held-out split for both models.',
        'Inference time deserves a caveat in the other direction: the quantum model is slower here by orders of magnitude because it simulates a state vector in software. That comparison says something about simulators, not about quantum processors.'
      ] },
    { id: 'limits', title: 'Limitations',
      body: [
        'No field validation. No multispectral or drone data is processed today; the architecture accepts it, the prototype does not have it. Labels in the evaluation dataset come from a forward-weather outbreak proxy, not from verified outbreak records, so every metric is a demonstration metric.',
        'The circuit runs on a simulator. Four qubits on a simulator is not a demonstration of quantum advantage and cannot be one. The vision model covers PlantVillage classes, which under-represents Indian field conditions, mixed cropping and late-stage symptoms.',
        'Sensor drift, calibration and device security are unsolved here. A deployed system would need per-device calibration history and a much stronger identity model than a prototype requires.'
      ] },
    { id: 'future', title: 'Future research',
      body: [
        'Nearest work: label a real dataset with agricultural university partners, replace the proxy labels, and re-run the same benchmark harness unchanged — the code path is already there.',
        'Then: multispectral and drone band inputs as additional features (NDVI, red-edge), data re-uploading circuits, kernel-based quantum methods for the small-sample regime, and execution on real quantum hardware through Qiskit Runtime to measure what noise does to a model this shallow.'
      ] }
  ];

  const TECH_STACK = [
    ['Frontend', 'HTML, CSS, vanilla JavaScript · responsive, offline-capable, EN/TE/HI ready'],
    ['Backend', 'FastAPI · Python 3.10+'],
    ['Computer vision', 'ONNX Runtime · PlantVillage classifier · Pillow image-quality screening'],
    ['Agricultural intelligence', 'Sensor, weather and context fusion with reliability weighting'],
    ['Classical ML', 'Logistic-regression baseline (scikit-learn when installed, bundled implementation otherwise)'],
    ['Quantum ML', 'Qiskit · 4-qubit variational classifier on the state-vector simulator'],
    ['Database', 'SQLite · schema kept PostgreSQL-portable'],
    ['Hardware', 'ESP32 · soil moisture, temperature, humidity (sketch included)'],
    ['Future inputs', 'Drone and multispectral imagery, satellite data, weather APIs — not implemented today']
  ];

  const ROADMAP = [
    ['Current', 'RGB crop imagery + field sensors + weather context', 'Implemented', 'ok'],
    ['Current', 'Experimental 4-qubit QML layer with classical baseline', 'Implemented · experimental', 'exp'],
    ['Next', 'Drone imagery ingestion', 'Future', 'future'],
    ['Next', 'Multispectral bands (NDVI, red-edge) as additional features', 'Future', 'future'],
    ['Next', 'Satellite data and regional weather APIs', 'Future', 'future'],
    ['Next', 'Large-scale field validation with agricultural partners', 'Future', 'future'],
    ['Future', 'Execution on real quantum hardware via Qiskit Runtime', 'Future', 'future'],
    ['Future', 'Regional and national agricultural intelligence network', 'Future', 'future']
  ];

  return { CROPS, DISEASES, SAFETY_NOTE, STATUS_BADGES, FLOW, RESEARCH, TECH_STACK, ROADMAP };
})();
