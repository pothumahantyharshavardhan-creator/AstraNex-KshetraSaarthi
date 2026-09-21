/* Localisation. Farmer-facing strings are translated; technical/institutional
   panels stay in English by design. Adding a language means adding one object
   here — no markup changes. */
window.AX_I18N = (function () {

  const STRINGS = {
    en: {
      status: { green: 'Field stable', amber: 'Check soon', red: 'Act today' },
      level: { STABLE: 'Stable', MONITOR: 'Monitor', 'EARLY WARNING': 'Early warning' },
      cropHealth: 'Crop health', diseaseRisk: 'Disease risk', waterStatus: 'Water status',
      heatStress: 'Heat stress', sensorConfidence: 'Sensor confidence', modelConfidence: 'Model confidence',
      recommended: 'Recommended action', nextCheck: 'Next check', analysing: 'Analysing field…',
      runScan: 'Analyse field', verify: 'Verification needed before acting',
      offline: 'Offline — scan stored on this device',
      simulated: 'Simulation data'
    },
    te: {
      status: { green: 'పొలం స్థిరంగా ఉంది', amber: 'త్వరలో చూడండి', red: 'ఈరోజే చర్య తీసుకోండి' },
      level: { STABLE: 'స్థిరం', MONITOR: 'గమనించండి', 'EARLY WARNING': 'ముందస్తు హెచ్చరిక' },
      cropHealth: 'పంట ఆరోగ్యం', diseaseRisk: 'తెగులు ప్రమాదం', waterStatus: 'నీటి స్థితి',
      heatStress: 'వేడి ఒత్తిడి', sensorConfidence: 'సెన్సార్ విశ్వసనీయత', modelConfidence: 'మోడల్ నమ్మకం',
      recommended: 'సూచించిన చర్య', nextCheck: 'తదుపరి తనిఖీ', analysing: 'పొలాన్ని విశ్లేషిస్తోంది…',
      runScan: 'పొలాన్ని విశ్లేషించండి', verify: 'చర్య తీసుకునే ముందు ధ్రువీకరణ అవసరం',
      offline: 'ఆఫ్‌లైన్ — స్కాన్ ఈ ఫోన్‌లో నిల్వ చేయబడింది',
      simulated: 'సిమ్యులేషన్ డేటా'
    },
    hi: {
      status: { green: 'खेत स्थिर है', amber: 'जल्द जांचें', red: 'आज ही कार्रवाई करें' },
      level: { STABLE: 'स्थिर', MONITOR: 'निगरानी रखें', 'EARLY WARNING': 'प्रारंभिक चेतावनी' },
      cropHealth: 'फसल स्वास्थ्य', diseaseRisk: 'रोग जोखिम', waterStatus: 'जल स्थिति',
      heatStress: 'ताप तनाव', sensorConfidence: 'सेंसर विश्वसनीयता', modelConfidence: 'मॉडल विश्वास',
      recommended: 'अनुशंसित कार्रवाई', nextCheck: 'अगली जांच', analysing: 'खेत का विश्लेषण हो रहा है…',
      runScan: 'खेत का विश्लेषण करें', verify: 'कार्रवाई से पहले पुष्टि आवश्यक है',
      offline: 'ऑफ़लाइन — स्कैन इस डिवाइस में सहेजा गया',
      simulated: 'सिमुलेशन डेटा'
    }
  };

  let current = localStorage.getItem('ax_lang') || 'en';

  function set(lang) {
    if (!STRINGS[lang]) return;
    current = lang;
    localStorage.setItem('ax_lang', lang);
    document.documentElement.setAttribute('data-lang', lang);
    document.querySelectorAll('.lang-switch button').forEach(b =>
      b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
    window.dispatchEvent(new CustomEvent('ax:lang', { detail: lang }));
  }

  function t(path, fallback) {
    const parts = path.split('.');
    let node = STRINGS[current];
    for (const p of parts) { node = node && node[p]; }
    if (node === undefined) {
      node = parts.reduce((n, p) => n && n[p], STRINGS.en);
    }
    return node === undefined ? (fallback || path) : node;
  }

  const lang = () => current;
  const cropName = crop => {
    const c = (window.AX_DATA.CROPS || []).find(x => x.id === crop);
    return c ? (c[current] || c.en) : crop;
  };

  return { set, t, lang, cropName, STRINGS };
})();
