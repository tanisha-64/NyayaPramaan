
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

