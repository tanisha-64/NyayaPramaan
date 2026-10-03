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
  const shouldRestartRef = useRef(false)
  const activeRef = useRef(false)

  // Keep callbacks fresh
  useEffect(() => { onResultRef.current = onResult }, [onResult])
  useEffect(() => { onInterimRef.current = onInterim }, [onInterim])

  const getSpeechRecognition = useCallback(() => {
    if (typeof window === 'undefined') return null
    return (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition || null
  }, [])

  const cleanupRecognition = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.abort() } catch { /* ignore */ }
      recognitionRef.current = null
    }
  }, [])

  const stopListening = useCallback(() => {
    activeRef.current = false
    shouldRestartRef.current = false
    cleanupRecognition()
    setInterimText('')
    setMicStatus('idle')
    setMicError(null)
  }, [cleanupRecognition])

  const startListening = useCallback(async () => {
    const SpeechRecognition = getSpeechRecognition()

    if (!SpeechRecognition) {
      setMicStatus('error')
      setMicError('not-supported')
      return
    }

    // Request mic permission explicitly first
    setMicStatus('requesting')
    setMicError(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Permission granted — stop the test stream immediately
      stream.getTracks().forEach((t) => t.stop())
    } catch (permErr: any) {
      setMicStatus('error')
      setMicError('not-allowed')
      return
    }

    // Clean up any stale instance
    cleanupRecognition()
    activeRef.current = true

    const createInstance = () => {
      if (!activeRef.current) return

      const recognition = new SpeechRecognition()
      // Hindi + English support — works for Hinglish too
      recognition.lang = 'hi-IN'
      recognition.continuous = true          // keep listening, don't stop after one phrase
      recognition.interimResults = true      // show live transcript as user speaks
      recognition.maxAlternatives = 1

      let finalBuffer = ''

      recognition.onstart = () => {
        setMicStatus('listening')
        setInterimText('')
        finalBuffer = ''
      }

      recognition.onresult = (event: any) => {
        let interimAccum = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          const transcript = result[0]?.transcript || ''
          if (result.isFinal) {
            finalBuffer += (finalBuffer ? ' ' : '') + transcript.trim()
            // Emit final text immediately
            onResultRef.current(finalBuffer.trim())
            finalBuffer = ''
            setInterimText('')
            if (onInterimRef.current) onInterimRef.current('')
          } else {
            interimAccum += transcript
          }
        }
        if (interimAccum) {
          setInterimText(interimAccum)
          if (onInterimRef.current) onInterimRef.current(interimAccum)
        }
      }

      recognition.onerror = (event: any) => {
        const err = event.error
        if (err === 'aborted' || !activeRef.current) return
        if (err === 'no-speech') {
          // Normal silence — auto-restart
          return
        }
        if (err === 'not-allowed') {
          setMicStatus('error')
          setMicError('not-allowed')
          activeRef.current = false
          return
        }
        if (err === 'network') {
          setMicStatus('error')
          setMicError('network')
          activeRef.current = false
          return
        }
        // For other errors (audio-capture etc.), try to restart silently
        console.warn('[useVoiceInput] Speech recognition notice:', err)
      }

      recognition.onend = () => {
        recognitionRef.current = null
        setInterimText('')
        // Auto-restart if still supposed to be listening
        if (activeRef.current && shouldRestartRef.current) {
          setTimeout(() => {
            if (activeRef.current) createInstance()
          }, 150)
        } else {
          setMicStatus('idle')
        }
      }

      recognitionRef.current = recognition
      shouldRestartRef.current = true
      try {
        recognition.start()
      } catch (e) {
        console.warn('[useVoiceInput] Start failed:', e)
        setMicStatus('error')
        setMicError('unknown')
        activeRef.current = false
      }
    }

    createInstance()
  }, [getSpeechRecognition, cleanupRecognition])

  const toggleListening = useCallback(() => {
    if (micStatus === 'listening' || micStatus === 'requesting') {
      stopListening()
    } else {
      startListening()
    }
  }, [micStatus, startListening, stopListening])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      activeRef.current = false
      shouldRestartRef.current = false
      cleanupRecognition()
    }
  }, [cleanupRecognition])

  const listening = micStatus === 'listening'

  return {
    listening,
    micStatus,
    micError,
    interimText,
    startListening,
    stopListening,
    toggleListening,
  }
}
