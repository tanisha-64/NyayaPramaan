'use client'
import { useState, useRef } from 'react'

export function useVoiceInput(onResult: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const recognitionRef = useRef<any>(null)

  function startListening() {
    setMicError(null)

    // Abort any previous instance first -- a stuck/unreleased previous
    // recognition instance is a common cause of "not-allowed" despite
    // the site having permission, because the browser treats the new
    // start() call as conflicting with an existing session.
    if (recognitionRef.current) {
      try { recognitionRef.current.abort() } catch {}
      recognitionRef.current = null
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (!SpeechRecognition) {
      setMicError('Voice input is not supported in this browser. Please use Chrome or Edge.')
      return
    }

    // Explicitly request mic permission SYNCHRONOUSLY within this click
    // handler (not after an await) -- Chrome can silently fail
    // SpeechRecognition's own permission prompt if it's not tied
    // directly to the user gesture.
    navigator.mediaDevices?.getUserMedia({ audio: true })
      .then((stream) => {
        stream.getTracks().forEach((t) => t.stop()) // we only needed the permission grant
        _startRecognition(SpeechRecognition)
      })
      .catch(() => {
        setMicError('Microphone permission denied. Click the lock icon in the address bar and allow microphone access for this site.')
      })
  }

  function _startRecognition(SpeechRecognition: any) {
    const recognition = new SpeechRecognition()
    recognition.lang = 'en-IN'
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onstart = () => setListening(true)
    recognition.onresult = (event: any) => onResult(event.results[0][0].transcript)
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      if (event.error === 'not-allowed') {
        setMicError('Microphone access was blocked. Check Chrome site-settings (lock icon → Microphone → Allow) and try again.')
      } else if (event.error === 'no-speech') {
        setMicError('No speech detected. Please try again.')
      } else if (event.error === 'network') {
        setMicError('Network error during voice recognition. Check your connection.')
      } else {
        setMicError(`Voice input error: ${event.error}`)
      }
      setListening(false)
      recognitionRef.current = null
    }
    recognition.onend = () => {
      setListening(false)
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    try {
      recognition.start()
    } catch (e) {
      console.error(e)
      setListening(false)
      setMicError('Could not start voice input. Please try again.')
    }
  }

  return { listening, startListening, micError }
}
