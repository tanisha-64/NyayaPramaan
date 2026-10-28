'use client'
import { useState, useRef } from 'react'

export function useVoiceOutput() {
  const [speakingId, setSpeakingId] = useState<string | null>(null)
  const [speechError, setSpeechError] = useState<string | null>(null)
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null)

  function speak(id: string, text: string) {
    setSpeechError(null)
    const synth = window.speechSynthesis
    if (!synth) {
      setSpeechError('Voice output is not supported in this browser. Please use Chrome or Edge.')
      return
    }

    // tap the same message again -> stop
    if (speakingId === id) {
      synth.cancel()
      setSpeakingId(null)
      return
    }

    synth.cancel() // stop whatever was speaking before

    const clean = text
      .replace(/[*_`#>\[\]()]/g, '')
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '')
      .trim()
    if (!clean) return

    const hasDevanagari = /[\u0900-\u097F]/.test(clean)
    const utter = new SpeechSynthesisUtterance(clean)
    utter.lang = hasDevanagari ? 'hi-IN' : 'en-IN'
    utter.onstart = () => setSpeakingId(id)
    utter.onend = () => setSpeakingId(null)
    utter.onerror = (e) => {
      if (e.error === 'interrupted' || e.error === 'canceled') return // normal when a new answer starts speaking
      setSpeechError('Could not play voice output. Please try again.')
      setSpeakingId(null)
    }

    utterRef.current = utter
    try {
      synth.speak(utter)
    } catch (e) {
      console.error(e)
      setSpeechError('Could not start voice output.')
      setSpeakingId(null)
    }
  }

  function stop() {
    window.speechSynthesis?.cancel()
    setSpeakingId(null)
  }

  return { speakingId, speak, stop, speechError }
}
