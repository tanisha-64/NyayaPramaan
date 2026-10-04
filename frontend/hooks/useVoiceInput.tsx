'use client'
import { useState, useRef, useCallback, useEffect } from 'react'

export type MicStatus = 'idle' | 'requesting' | 'listening' | 'error'
export type MicErrorType = 'not-allowed' | 'not-supported' | 'network' | 'unknown'

export function useVoiceInput(
  onResult: (text: string) => void,
  onInterim?: (text: string) => void
) {
  const [micStatus, setMicStatus] = useState<MicStatus>('idle')
  const [micError, setMicError] = useState<MicErrorType | null>(null)
  const [interimText, setInterimText] = useState('')

  const recognitionRef = useRef<any>(null)
  const onResultRef = useRef(onResult)
  const onInterimRef = useRef(onInterim)
  const isListeningRef = useRef(false)

  // Keep callbacks fresh
  useEffect(() => { onResultRef.current = onResult }, [onResult])
  useEffect(() => { onInterimRef.current = onInterim }, [onInterim])

  const getSpeechRecognition = useCallback(() => {
    if (typeof window === 'undefined') return null
    return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null
  }, [])

  const stopListening = useCallback(() => {
    isListeningRef.current = false
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        try { recognitionRef.current.abort() } catch {}
      }
      recognitionRef.current = null
    }
    setInterimText('')
    setMicStatus('idle')
  }, [])

  const startListening = useCallback(() => {
    const SpeechRecognition = getSpeechRecognition()

    if (!SpeechRecognition) {
      setMicStatus('error')
      setMicError('not-supported')
      return
    }

    if (recognitionRef.current) {
      try { recognitionRef.current.abort() } catch {}
      recognitionRef.current = null
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-IN' // Supports English and Indian accents; also parses Hinglish
      recognition.maxAlternatives = 1

      recognition.onstart = () => {
        isListeningRef.current = true
        setMicStatus('listening')
        setMicError(null)
        setInterimText('')
      }

      recognition.onresult = (event: any) => {
        let interim = ''
        let finalChunk = ''

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i]
          const transcript = res[0]?.transcript || ''
          if (res.isFinal) {
            finalChunk += transcript
          } else {
            interim += transcript
          }
        }

        if (finalChunk.trim()) {
          onResultRef.current(finalChunk.trim())
          setInterimText('')
          if (onInterimRef.current) onInterimRef.current('')
        } else if (interim) {
          setInterimText(interim)
          if (onInterimRef.current) onInterimRef.current(interim)
        }
      }

      recognition.onerror = (event: any) => {
        const err = event.error
        if (err === 'aborted' || !isListeningRef.current) return
        if (err === 'no-speech') {
          return // normal silence
        }
        if (err === 'not-allowed') {
          setMicStatus('error')
          setMicError('not-allowed')
          isListeningRef.current = false
          return
        }
        if (err === 'network') {
          setMicStatus('error')
          setMicError('network')
          isListeningRef.current = false
          return
        }
        console.warn('[useVoiceInput] Speech recognition event:', err)
      }

      recognition.onend = () => {
        if (isListeningRef.current) {
          // Restart gracefully if user hasn't explicitly stopped
          try {
            recognition.start()
          } catch {
            setMicStatus('idle')
            isListeningRef.current = false
          }
        } else {
          setMicStatus('idle')
        }
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (e: any) {
      console.warn('[useVoiceInput] Direct start failed:', e)
      setMicStatus('error')
      setMicError('unknown')
      isListeningRef.current = false
    }
  }, [getSpeechRecognition])

  const toggleListening = useCallback(() => {
    if (micStatus === 'listening') {
      stopListening()
    } else {
      startListening()
    }
  }, [micStatus, startListening, stopListening])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isListeningRef.current = false
      if (recognitionRef.current) {
        try { recognitionRef.current.abort() } catch {}
        recognitionRef.current = null
      }
    }
  }, [])

  return {
    listening: micStatus === 'listening',
    micStatus,
    micError,
    interimText,
    startListening,
    stopListening,
    toggleListening,
  }
}
