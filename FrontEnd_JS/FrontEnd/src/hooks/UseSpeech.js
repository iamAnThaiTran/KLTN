import { useState, useEffect, useRef } from 'react';

/**
 * Manages Web Speech API (Vietnamese recognition).
 * Returns: { isListening, transcript, isBrowserSupported, toggle, inputRef }
 * `inputRef` is not used internally—caller appends final text to its own state via `onFinalTranscript`.
 */
export const useSpeech = ({ onFinalTranscript }) => {
  const [isListening, setIsListening]           = useState(false);
  const [transcript, setTranscript]             = useState('');
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setIsBrowserSupported(false); return; }

    const r = new SR();
    r.continuous      = true;
    r.interimResults  = true;
    r.lang            = 'vi-VN';

    r.onstart  = () => { setIsListening(true); setTranscript(''); };
    r.onresult = (e) => {
      let interim = '', final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t + ' '; else interim += t;
      }
      setTranscript(interim);
      if (final) onFinalTranscript(final.trim());
    };
    r.onerror = () => setIsListening(false);
    r.onend   = () => { setIsListening(false); setTranscript(''); };

    recognitionRef.current = r;
    return () => recognitionRef.current?.abort();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = () => {
    if (!recognitionRef.current) return;
    if (isListening) recognitionRef.current.stop();
    else try { recognitionRef.current.start(); } catch (e) { console.error(e); }
  };

  return { isListening, transcript, isBrowserSupported, toggle };
};