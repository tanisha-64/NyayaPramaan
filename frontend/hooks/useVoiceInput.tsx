'use client'
import { useState, useRef, useCallback, useEffect } from 'react'

export function useVoiceInput(onResult: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef<any>(null)
  const onResultRef = useRef(onResult)

  useEffect(() => {
    onResultRef.current = onResult
  }, [onResult])

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // ignore already stopped
      }
      recognitionRef.current = null
    }
    setListening(false)
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognition =
      typeof window !== 'undefined'
        ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        : null

    if (!SpeechRecognition) {
      console.warn('Speech recognition not supported in this browser.')
      return
    }

    // Stop any existing instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort()
      } catch {
        // ignore
      }
      recognitionRef.current = null
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.lang = 'en-IN'
      recognition.continuous = false
      recognition.interimResults = false

      recognition.onstart = () => {
        setListening(true)
      }

      recognition.onresult = (event: any) => {
        if (event.results && event.results[0] && event.results[0][0]) {
          const transcript = event.results[0][0].transcript
          if (transcript && transcript.trim()) {
            onResultRef.current(transcript.trim())
          }
        }
      }

      recognition.onerror = (event: any) => {
        const err = event.error
        // 'no-speech' and 'aborted' are normal user lifecycle events -- handle silently
        if (err === 'no-speech' || err === 'aborted') {
          setListening(false)
          return
        }

        if (err === 'not-allowed') {
          console.warn('Microphone permission denied.')
        } else {
          console.warn('Speech recognition notice:', err)
        }
        setListening(false)
      }

      recognition.onend = () => {
        setListening(false)
        recognitionRef.current = null
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (e) {
      console.warn('Speech recognition start failed:', e)
      setListening(false)
    }
  }, [])

  const toggleListening = useCallback(() => {
    if (listening) {
      stopListening()
    } else {
      startListening()
    }
  }, [listening, startListening, stopListening])

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {
          // cleanup
        }
      }
    }
  }, [])

  return { listening, startListening, stopListening, toggleListening }
}
