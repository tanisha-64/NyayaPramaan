
'use client'

import { useState, useRef } from 'react'



export function useVoiceInput(onResult: (text: string) => void) {

  const [listening, setListening] = useState(false)

  const recognitionRef = useRef<any>(null)



  function startListening() {

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

    if (!SpeechRecognition) {

      alert('Voice input not supported in this browser. Please use Chrome or Edge.')

      return

    }

    if (listening) return



    const recognition = new SpeechRecognition()

    recognition.lang = 'en-IN'

    recognition.continuous = false

    recognition.interimResults = false



    recognition.onstart = () => setListening(true)

    recognition.onresult = (event: any) => onResult(event.results[0][0].transcript)

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      setListening(false)
      if (event.error === 'not-allowed') {
        alert('Microphone permission is blocked. Please allow microphone access in your browser settings (click the lock/camera icon in the address bar).')
      }
    }


    recognition.onend = () => setListening(false)



    recognitionRef.current = recognition

    try {

      recognition.start()

    } catch (e) {

      console.error(e)

      setListening(false)

    }

  }



  return { listening, startListening }

}

